#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.

import logging
import traceback
import datetime
from multiprocessing.dummy import Pool as ThreadPool

from django.conf import settings
from django.core.management.base import BaseCommand
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from meeting.infrastructure.adapter.message_adapter_impl.email_adapter_impl import EmailAdapter
from meeting.infrastructure.dao import meeting_dao, meeting_cycle_sub_dao

logger = logging.getLogger("log")


class HandleOvertimeMeeting:
    """超时会议检测处理类"""
    meeting_dao = meeting_dao.MeetingDao
    _meeting_cycle_sub_dao = meeting_cycle_sub_dao.MeetingCycleSubMeetingDao

    def __init__(self, community):
        self.community = community

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


def work_flow(handler: HandleOvertimeMeeting):
    """工作流"""
    try:
        handler.detect_overtime_meetings()
    except Exception as e:
        logger.error("[handle_overtime_meeting] detect_overtime_meetings:{}, traceback:{}".format(str(e), traceback.format_exc()))
    try:
        handler.send_overtime_warning_email()
    except Exception as e:
        logger.error("[handle_overtime_meeting] send_overtime_warning_email:{}, traceback:{}".format(str(e), traceback.format_exc()))


class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info('-' * 20 + ' start to handle overtime meeting' + '-' * 20)
        logger.info('[handle_overtime] find community: {}'.format(",".join(settings.COMMUNITY_SUPPORT)))
        try:
            handlers = [HandleOvertimeMeeting(i) for i in settings.COMMUNITY_SUPPORT]
            pool = ThreadPool()
            pool.map(work_flow, handlers)
            pool.close()
            pool.join()
            logger.info('-' * 20 + 'All done' + '-' * 20)
        except Exception as e:
            logger.error("[handle_overtime] err:{}, traceback:{}".format(str(e), traceback.format_exc()))