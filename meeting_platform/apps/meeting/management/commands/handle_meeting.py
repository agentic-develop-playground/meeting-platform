#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.

import logging
import traceback
import datetime
from enum import Enum
from multiprocessing.dummy import Pool as ThreadPool

from django.conf import settings
from django.core.management.base import BaseCommand
from django.forms import model_to_dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl import MeetingAdapterImpl
from meeting.infrastructure.adapter.message_adapter_impl.email_adapter_impl import EmailAdapter
from meeting.infrastructure.dao import meeting_dao, meeting_participants_dao, meeting_cycle_sub_dao

logger = logging.getLogger("log")


class MeetingSchedulePlan(Enum):
    WINDOWS = "windows"
    DEFAULT = "point"

    @classmethod
    def from_settings(cls):
        """从settings获取当前计划类型"""
        schedule_plan = settings.HANDLE_MEETING_SCHEDULE_PLAN.lower()
        for plan in cls:
            if plan.value == schedule_plan:
                return plan
        return cls.DEFAULT


class HandleMeeting:
    meeting_dao = meeting_dao.MeetingDao
    _meeting_participants_dao = meeting_participants_dao.MeetingParticipantsDao
    _meeting_cycle_sub_dao = meeting_cycle_sub_dao.MeetingCycleSubMeetingDao
    meeting_adapter_impl = MeetingAdapterImpl()

    def __init__(self, community):
        self.community = community

    @staticmethod
    def _get_windows_meeting():
        cur_date = datetime.datetime.now()
        today_date = cur_date.strftime('%Y-%m-%d')
        start_time = (cur_date - datetime.timedelta(minutes=2 * settings.FORCE_MEETING_END_TIME)).strftime("%H:%M")
        end_time = (cur_date - datetime.timedelta(minutes=settings.FORCE_MEETING_END_TIME)).strftime("%H:%M")
        return today_date, start_time, end_time

    @staticmethod
    def _get_point_meeting():
        cur_date = datetime.datetime.now()
        start_date = (cur_date - datetime.timedelta(hours=settings.FORCE_MEETING_END_POINT)).strftime("%Y-%m-%d")
        end_date = cur_date.strftime("%Y-%m-%d")
        return start_date, end_date

    def _get_over_meeting_by_windows(self):
        """会议30分钟后统计数据和自动结束会议"""
        # fix: 当天的mid是否存在重复的可能性？ 一般是不可能，但保险的方式是：结束只执行一次：设置定时器的时间为每15分钟，查询结束的时间是否在结束后15分钟~30分钟之内。
        # resolve: cur_datetime-30 < end_time  < cur_datetime-15
        today_date, start_time, end_time = self._get_windows_meeting()
        return self.meeting_dao.get_windows_meeting(self.community, today_date, start_time, end_time)

    def _get_over_meeting_by_point(self):
        """每天凌晨统计数据和强制结束会议"""
        start_date, end_date = self._get_point_meeting()
        return self.meeting_dao.get_point_meeting(self.community, start_date, end_date)

    def _get_cur_day_meeting(self):
        if MeetingSchedulePlan.from_settings() == MeetingSchedulePlan.WINDOWS:
            return self._get_over_meeting_by_windows()
        else:
            return self._get_over_meeting_by_point()

    def refresh_meeting_participants(self):
        meetings = self._get_cur_day_meeting()
        for meeting in meetings:
            meeting_info = self._meeting_participants_dao.get(meeting.id)
            if not meeting_info:
                logger.info("start to handle meeting:{}".format(meeting.id))
                meeting_dict = model_to_dict(meeting)
                if meeting_dict["is_cycle"]:
                    sub_meeting_info = self._meeting_cycle_sub_dao.get_by_mid_date(meeting_dict["mid"],
                                                                                   datetime.datetime.now().strftime(
                                                                                       '%Y-%m-%d'))
                    if sub_meeting_info:
                        meeting_dict["date"] = sub_meeting_info["date"]
                        meeting_dict["start"] = sub_meeting_info["start"]
                        meeting_dict["end"] = sub_meeting_info["end"]
                    else:
                        continue
                meeting_participants = self.meeting_adapter_impl.get_participants(meeting_dict)
                if meeting_participants.get("participants"):
                    participants = [user["name"] for user in meeting_participants["participants"]]
                    deduplication_participants = list(set(participants))
                    data = {
                        "meeting": meeting,
                        "participants": ",".join(deduplication_participants)
                    }
                    self._meeting_participants_dao.create(**data)

    def force_stop_meeting(self):
        meetings = self._get_cur_day_meeting()
        for meeting in meetings:
            self.meeting_adapter_impl.force_end_meeting(model_to_dict(meeting))

    def sync_meeting_status(self):
        """同步会议状态"""
        now = datetime.datetime.now()
        meetings = self.meeting_dao.get_ongoing_candidates(self.community, now)

        for meeting in meetings:
            try:
                meeting_dict = model_to_dict(meeting)

                # 非周期会议
                if not meeting.is_cycle:
                    previous_ongoing = meeting.is_ongoing
                    is_ongoing = self.meeting_adapter_impl.get_meeting_status(meeting_dict)
                    self.meeting_dao.update_status(meeting.id, is_ongoing)
                    # 如果会议从"未进行中"变为"进行中"，重置预警邮件状态
                    if not previous_ongoing and is_ongoing:
                        self.meeting_dao.reset_warning_email_status(meeting.id)
                        logger.info('[sync_meeting_status] meeting {} started, reset warning_email_sent'.format(meeting.mid))
                    # 如果会议已结束，清除超时状态
                    if not is_ongoing and meeting.is_overtime:
                        self.meeting_dao.clear_overtime_status(meeting.id)
                    logger.info('[sync_meeting_status] meeting {} status updated to {}'.format(meeting.mid, is_ongoing))
                else:
                    # 周期会议：查询每个子会议
                    sub_meetings = self._meeting_cycle_sub_dao.get_by_mid(meeting.mid)
                    for sub in sub_meetings:
                        # 只同步今天的子会议或正在进行中的子会议
                        sub_date = sub.get('date')
                        if sub_date != now.strftime('%Y-%m-%d') and not sub.get('is_ongoing'):
                            continue
                        meeting_dict["sub_id"] = sub.get('sub_id')
                        previous_ongoing = sub.get('is_ongoing')
                        is_ongoing = self.meeting_adapter_impl.get_meeting_status(meeting_dict)
                        self._meeting_cycle_sub_dao.update_status(sub.get('id'), is_ongoing)
                        # 如果子会议从"未进行中"变为"进行中"，重置预警邮件状态
                        if not previous_ongoing and is_ongoing:
                            self._meeting_cycle_sub_dao.reset_warning_email_status(sub.get('sub_id'))
                            logger.info('[sync_meeting_status] sub meeting {}/{} started, reset warning_email_sent'
                                        .format(meeting.mid, sub.get('sub_id')))
                        # 如果子会议已结束，清除超时状态
                        if not is_ongoing and sub.get('is_overtime'):
                            self._meeting_cycle_sub_dao.clear_overtime_status(sub.get('sub_id'))
                        logger.info('[sync_meeting_status] sub meeting {}/{} status updated to {}'
                                    .format(meeting.mid, sub.get('sub_id'), is_ongoing))
            except Exception as e:
                logger.error("[sync_meeting_status] meeting {} error: {}, traceback: {}"
                             .format(meeting.mid, str(e), traceback.format_exc()))

    def detect_overtime_meetings(self):
        """检测超时会议并更新标记"""
        now = datetime.datetime.now()
        today = now.strftime('%Y-%m-%d')

        try:
            # 检测非周期会议
            overtime_meetings = self.meeting_dao.get_overtime_meetings(self.community, today)
            for meeting in overtime_meetings:
                if not meeting.is_overtime:
                    self.meeting_dao.update_overtime_status(meeting.id, True)
                    logger.warning('[detect_overtime_meetings] meeting {} is overtime, detected at {}'
                                   .format(meeting.mid, now))

            # 检测周期会议子会议
            overtime_sub_meetings = self._meeting_cycle_sub_dao.get_overtime_sub_meetings(self.community, today)
            for sub_meeting in overtime_sub_meetings:
                if not sub_meeting.is_overtime:
                    self._meeting_cycle_sub_dao.update_overtime_status(sub_meeting.id, True)
                    logger.warning('[detect_overtime_meetings] sub meeting {} is overtime, detected at {}'
                                   .format(sub_meeting.sub_id, now))
        except Exception as e:
            logger.error("[detect_overtime_meetings] error: {}, traceback: {}"
                         .format(str(e), traceback.format_exc()))

    def send_overtime_warning_email(self):
        """发送超时预警邮件（会议结束前5分钟）"""
        now = datetime.datetime.now()
        today = now.strftime('%Y-%m-%d')

        # 获取运营邮箱配置
        operator_emails = settings.OPERATOR_EMAILS.get(self.community, [])
        if not operator_emails:
            logger.debug('[send_overtime_warning_email] no operator emails configured for community {}'
                         .format(self.community))
            return

        try:
            # 获取即将结束的非周期会议
            upcoming_meetings = self.meeting_dao.get_upcoming_end_meetings(self.community, today)
            for meeting in upcoming_meetings:
                self._send_warning_email(meeting, operator_emails)

            # 获取即将结束的周期子会议
            upcoming_sub_meetings = self._meeting_cycle_sub_dao.get_upcoming_end_sub_meetings(self.community, today)
            for sub_meeting in upcoming_sub_meetings:
                self._send_warning_email(sub_meeting.meeting, operator_emails, sub_meeting)
        except Exception as e:
            logger.error("[send_overtime_warning_email] error: {}, traceback: {}"
                         .format(str(e), traceback.format_exc()))

    def _send_warning_email(self, meeting, operator_emails, sub_meeting=None):
        """发送单封预警邮件"""
        try:
            # 获取平台名称
            platform = meeting.platform.replace('TENCENT', 'Tencent') \
                .replace('WELINK', 'WeLink').replace("ZOOM", 'Zoom')

            # 构建邮件内容
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

            logger.info('[send_overtime_warning_email] sent warning email for meeting {} to {}'
                        .format(meeting_id, operator_emails))
        except Exception as e:
            logger.error("[_send_warning_email] error for meeting {}: {}, traceback: {}"
                         .format(meeting.mid, str(e), traceback.format_exc()))


def work_flow(handle_meeting: HandleMeeting):
    try:
        handle_meeting.sync_meeting_status()
    except Exception as e:
        logger.error("[handle_meeting] sync_meeting_status:{}, traceback:{}".format(str(e), traceback.format_exc()))
    try:
        handle_meeting.detect_overtime_meetings()
    except Exception as e:
        logger.error("[handle_meeting] detect_overtime_meetings:{}, traceback:{}".format(str(e), traceback.format_exc()))
    try:
        handle_meeting.send_overtime_warning_email()
    except Exception as e:
        logger.error("[handle_meeting] send_overtime_warning_email:{}, traceback:{}".format(str(e), traceback.format_exc()))
    try:
        handle_meeting.force_stop_meeting()
    except Exception as e:
        logger.error("[handle_meeting] force_stop_meeting:{}, traceback:{}".format(str(e), traceback.format_exc()))
    try:
        handle_meeting.refresh_meeting_participants()
    except Exception as e:
        logger.error(
            "[handle_meeting] refresh_meeting_participants:{}, traceback:{}".format(str(e), traceback.format_exc()))


class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info('-' * 20 + ' start to handle meeting' + '-' * 20)
        logger.info('[handle] find community: {}'.format(",".join(settings.COMMUNITY_SUPPORT)))
        try:
            handler_recording_communities = [HandleMeeting(i) for i in settings.COMMUNITY_SUPPORT]
            pool = ThreadPool()
            pool.map(work_flow, handler_recording_communities)
            pool.close()
            pool.join()
            logger.info('-' * 20 + 'All done' + '-' * 20)
        except Exception as e:
            logger.error("[handle_recordings/handle] err:{}, traceback:{}".format(str(e), traceback.format_exc()))
