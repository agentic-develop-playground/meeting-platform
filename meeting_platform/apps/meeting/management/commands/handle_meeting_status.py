#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.

import logging
import traceback
import datetime
from multiprocessing.dummy import Pool as ThreadPool

from django.conf import settings
from django.core.management.base import BaseCommand
from django.forms import model_to_dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from meeting.domain.primitive.meeting_status import BusinessMeetingStatus
from meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl import MeetingAdapterImpl
from meeting.infrastructure.adapter.message_adapter_impl.email_adapter_impl import EmailAdapter
from meeting.infrastructure.dao import meeting_dao, meeting_cycle_sub_dao

logger = logging.getLogger("log")


class HandleMeetingStatus:
    """会议状态同步和预警邮件处理类"""
    meeting_dao = meeting_dao.MeetingDao
    _meeting_cycle_sub_dao = meeting_cycle_sub_dao.MeetingCycleSubMeetingDao
    meeting_adapter_impl = MeetingAdapterImpl()

    def __init__(self, community):
        self.community = community

    def sync_meeting_status(self):
        """同步会议状态（从第三方API获取实时状态）"""
        now = datetime.datetime.now()
        today = now.strftime('%Y-%m-%d')

        # 获取大于等于今天所有会议（无时间窗口）
        meetings = self.meeting_dao.get_status_sync_candidates(self.community, now)

        for meeting in meetings:
            try:
                meeting_dict = model_to_dict(meeting)

                if not meeting.is_cycle:
                    # 非周期会议处理
                    self._sync_single_meeting(meeting, meeting_dict, now)
                else:
                    # 周期会议：处理大于等于今天的每个子会议
                    sub_meetings = self._meeting_cycle_sub_dao.get_status_sync_candidates(
                        self.community, today
                    )
                    for sub in sub_meetings:
                        if sub.mid != meeting.mid:
                            continue
                        meeting_dict["sub_id"] = sub.sub_id
                        self._sync_sub_meeting(meeting, sub, meeting_dict, now)

            except Exception as e:
                logger.error("[sync_status] meeting {} error: {}, traceback: {}"
                             .format(meeting.mid, str(e), traceback.format_exc()))

    def _sync_single_meeting(self, meeting, meeting_dict, now):
        """同步单个非周期会议状态"""
        previous_status = meeting.status

        # 从第三方API获取实时状态
        api_status = self.meeting_adapter_impl.get_meeting_status(meeting_dict)

        # 计算业务状态
        new_status = self._calculate_status(meeting.date, meeting.start, meeting.end, api_status, now)

        # 更新数据库
        if new_status != previous_status:
            self.meeting_dao.update_status(meeting.id, new_status)
            logger.info('[sync_status] meeting {} status: {} -> {}'
                        .format(meeting.mid, previous_status, new_status))

        # 会议开始时重置预警邮件状态
        if previous_status == BusinessMeetingStatus.NOT_STARTED.value and new_status == BusinessMeetingStatus.ONGOING.value:
            self.meeting_dao.reset_warning_email_status(meeting.id)
            logger.info('[sync_status] meeting {} started, reset warning_email_sent'
                        .format(meeting.mid))

    def _sync_sub_meeting(self, meeting, sub, meeting_dict, now):
        """同步周期子会议状态"""
        previous_status = sub.status

        # 从第三方API获取实时状态
        api_status = self.meeting_adapter_impl.get_meeting_status(meeting_dict)

        # 计算业务状态
        new_status = self._calculate_status(sub.date, sub.start, sub.end, api_status, now)

        # 更新数据库
        if new_status != previous_status:
            self._meeting_cycle_sub_dao.update_status(sub.id, new_status)
            logger.info('[sync_status] sub meeting {}/{} status: {} -> {}'
                        .format(meeting.mid, sub.sub_id, previous_status, new_status))

        # 子会议开始时重置预警邮件状态
        if previous_status == BusinessMeetingStatus.NOT_STARTED.value and new_status == BusinessMeetingStatus.ONGOING.value:
            self._meeting_cycle_sub_dao.reset_warning_email_status(sub.sub_id)
            logger.info('[sync_status] sub meeting {}/{} started, reset warning_email_sent'
                        .format(meeting.mid, sub.sub_id))

    @staticmethod
    def _calculate_status(date, start, end, api_status, now):
        """根据当前时间和会议时间计算业务状态

        状态判断规则：
        - 当前时间 < 开始时间 且 实时会议未举行 → 未开始(0)
        - 当前时间在会议时间段内 或 实时会议在进行中 → 进行中(1)
        - 当前时间 > 结束时间 且 实时会议已结束 → 已结束(2)
        - 当前时间 > 结束时间 且 实时会议未结束 → 已超时(3)
        """
        if not date or not start or not end:
            return BusinessMeetingStatus.NOT_STARTED.value

        try:
            meeting_start_time = datetime.datetime.strptime(f"{date} {start}", "%Y-%m-%d %H:%M")
            meeting_end_time = datetime.datetime.strptime(f"{date} {end}", "%Y-%m-%d %H:%M")
        except ValueError:
            return BusinessMeetingStatus.NOT_STARTED.value

        # 实时会议正在进行中
        if api_status:
            # 超过结束时间但会议仍在进行 → 超时(3)
            if now > meeting_end_time:
                return BusinessMeetingStatus.OVERTIME.value
            return BusinessMeetingStatus.ONGOING.value

        # 实时会议未在进行中
        # 当前时间 < 开始时间 → 未开始(0)
        if now < meeting_start_time:
            return BusinessMeetingStatus.NOT_STARTED.value

        # 当前时间在会议时间段内但API返回未进行 → 进行中(1)
        if meeting_start_time <= now <= meeting_end_time:
            return BusinessMeetingStatus.ONGOING.value

        # 当前时间 > 结束时间 且 API未进行中 → 已结束(2)
        return BusinessMeetingStatus.ENDED.value

    def send_warning_emails(self):
        """发送预警邮件

        简化逻辑：在下一场会议开始前 WARNING_ADVANCE_TIME（30分钟）发送预警
        """
        now = datetime.datetime.now()
        today = now.strftime('%Y-%m-%d')

        # 获取运营邮箱配置
        operator_emails = settings.OPERATOR_EMAILS.get(self.community, [])
        if not operator_emails:
            logger.debug('[send_warning_emails] no operator emails configured for community {}'
                         .format(self.community))
            return

        try:
            # 获取所有需要预警检查的会议（进行中/超时且未发送预警）
            ongoing_meetings = self.meeting_dao.get_ongoing_meetings_for_warning(self.community, today)

            for meeting in ongoing_meetings:
                # 获取下一场会议的开始时间
                next_start = self._get_next_meeting_start_time(
                    meeting.host_id, today, meeting.end
                )

                if next_start is None:
                    # 无后续会议，跳过
                    logger.debug('[send_warning_emails] meeting {} has no subsequent meetings, skip'
                                 .format(meeting.mid))
                    continue

                # 判断是否应该发送预警（简化后只需要 next_start）
                if self._should_send_warning(next_start, now):
                    self._send_warning_email(meeting, operator_emails)

            # 同样处理周期子会议
            ongoing_sub_meetings = self._meeting_cycle_sub_dao.get_ongoing_sub_meetings_for_warning(
                self.community, today
            )

            for sub_meeting in ongoing_sub_meetings:
                # 获取下一场会议的开始时间
                next_start = self._get_next_meeting_start_time(
                    sub_meeting.meeting.host_id, today, sub_meeting.end
                )

                if next_start is None:
                    # 无后续会议，跳过
                    logger.debug('[send_warning_emails] sub meeting {}/{} has no subsequent meetings, skip'
                                 .format(sub_meeting.mid, sub_meeting.sub_id))
                    continue

                # 判断是否应该发送预警（简化后只需要 next_start）
                if self._should_send_warning(next_start, now):
                    self._send_warning_email(sub_meeting.meeting, operator_emails, sub_meeting)

        except Exception as e:
            logger.error("[send_warning_emails] error: {}, traceback: {}"
                         .format(str(e), traceback.format_exc()))

    def _get_next_meeting_start_time(self, host_id, today, current_end_time):
        """获取下一场会议的开始时间（综合非周期和周期）

        Args:
            host_id: 会议主持人邮箱
            today: 今天日期
            current_end_time: 当前会议结束时间

        Returns:
            str: 下一场会议的开始时间 (HH:MM)，如果没有后续会议返回 None
        """
        # 从非周期会议中获取
        non_cycle_start = self.meeting_dao.get_next_meeting_start_time(
            self.community, host_id, today, current_end_time
        )
        # 从周期子会议中获取
        cycle_start = self._meeting_cycle_sub_dao.get_next_sub_meeting_start_time(
            self.community, host_id, today, current_end_time
        )

        # 返回最早的一个
        starts = [s for s in [non_cycle_start, cycle_start] if s]
        return min(starts) if starts else None

    @staticmethod
    def _should_send_warning(next_meeting_start_time, now):
        """判断是否应该发送预警

        简化逻辑：在下一场会议开始前 WARNING_ADVANCE_TIME 分钟发送预警

        Args:
            next_meeting_start_time: 下一场会议开始时间 (HH:MM)
            now: 当前时间

        Returns:
            bool: 是否应该发送预警
        """
        # 从配置获取参数
        warning_advance_time = settings.OVER_TIME_WARNING_ADVANCE_TIME  # 分钟

        today_str = now.strftime('%Y-%m-%d')

        try:
            # 计算预警时间：下一场会议开始前 N 分钟
            next_start_dt = datetime.datetime.strptime(f"{today_str} {next_meeting_start_time}", "%Y-%m-%d %H:%M")
            warning_time = next_start_dt - datetime.timedelta(minutes=warning_advance_time)

            # 当前时间在预警时间点附近（前后1分钟容差）
            time_diff = abs((now - warning_time).total_seconds())
            return time_diff <= 60  # 1分钟容差

        except ValueError as e:
            logger.error("[_should_send_warning] time parsing error: {}".format(str(e)))
            return False

    def _send_warning_email(self, meeting, operator_emails, sub_meeting=None):
        """发送单封预警邮件"""
        try:
            platform = meeting.platform.replace('TENCENT', 'Tencent') \
                .replace('WELINK', 'WeLink').replace("ZOOM", 'Zoom')

            subject = '[Warning] Meeting about to end - {}'.format(meeting.topic)

            if sub_meeting:
                end_time = sub_meeting.end
                meeting_id = '{}/{}'.format(meeting.mid, sub_meeting.sub_id)
            else:
                end_time = meeting.end
                meeting_id = meeting.mid

            body = """
Meeting is about to end in 5 minutes and may require attention:

Topic: {}
Meeting ID: {}
Platform: {}
Scheduled End Time: {}
Sponsor: {}
SIG: {}

Please check if the meeting needs intervention.
            """.format(meeting.topic, meeting_id, platform, end_time,
                       meeting.sponsor, meeting.group_name)

            msg = MIMEMultipart()
            msg.attach(MIMEText(body, _charset='utf-8'))
            msg['Subject'] = subject
            msg['To'] = ','.join(operator_emails)

            email_adapter = EmailAdapter(self.community)
            email_adapter.send_message(operator_emails, msg)

            # 标记已发送预警邮件
            if sub_meeting:
                self._meeting_cycle_sub_dao.mark_warning_email_sent(sub_meeting.id)
            else:
                self.meeting_dao.mark_warning_email_sent(meeting.id)

            logger.info('[send_warning_emails] sent warning email for meeting {} to {}'
                        .format(meeting_id, operator_emails))
        except Exception as e:
            logger.error("[_send_warning_email] error for meeting {}: {}, traceback: {}"
                         .format(meeting.mid, str(e), traceback.format_exc()))


def work_flow(handler: HandleMeetingStatus):
    """工作流"""
    try:
        handler.sync_meeting_status()
    except Exception as e:
        logger.error("[handle_meeting_status] sync_meeting_status:{}, traceback:{}"
                     .format(str(e), traceback.format_exc()))
    try:
        handler.send_warning_emails()
    except Exception as e:
        logger.error("[handle_meeting_status] send_warning_emails:{}, traceback:{}"
                     .format(str(e), traceback.format_exc()))

# 定时器每5分钟执行一次
class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info('-' * 20 + ' start to handle meeting status' + '-' * 20)
        logger.info('[handle_meeting_status] find community: {}'
                    .format(",".join(settings.COMMUNITY_SUPPORT)))
        try:
            handlers = [HandleMeetingStatus(i) for i in settings.COMMUNITY_SUPPORT]
            pool = ThreadPool()
            pool.map(work_flow, handlers)
            pool.close()
            pool.join()
            logger.info('-' * 20 + 'All done' + '-' * 20)
        except Exception as e:
            logger.error("[handle_meeting_status] err:{}, traceback:{}"
                         .format(str(e), traceback.format_exc()))