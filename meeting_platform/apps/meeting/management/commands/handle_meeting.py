#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2025/3/19 9:56
# @Author  : Tom_zc
# @FileName: handle_meeting.py
# @Software: PyCharm

import logging
import traceback
import datetime
from multiprocessing.dummy import Pool as ThreadPool

from django.conf import settings
from django.core.management.base import BaseCommand
from django.forms import model_to_dict

from meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl import MeetingAdapterImpl
from meeting.infrastructure.dao import meeting_dao, meeting_participants_dao

logger = logging.getLogger("log")


class HandleMeeting:
    meeting_dao = meeting_dao.MeetingDao
    meeting_participants_dao = meeting_participants_dao.MeetingParticipantsDao
    meeting_adapter_impl = MeetingAdapterImpl()

    def __init__(self, community):
        self.community = community

    @staticmethod
    def _get_valid_query_range():
        cur_date = datetime.datetime.now()
        start_date = (cur_date - datetime.timedelta(days=settings.QUERY_MEETING_DATE)).strftime('%Y-%m-%d')
        end_date = cur_date.strftime('%Y-%m-%d')
        hour = f"{cur_date.hour:02}"
        minute = f"{cur_date.minute:02}"
        return start_date, end_date, f"{hour}:{minute}"

    def _get_over_meeting(self):
        start_date, end_date, end_time = self._get_valid_query_range()
        return self.meeting_dao.get_meeting_by_date(self.community, start_date, end_date, end_time)

    @staticmethod
    def _get_today_end_meeting():
        cur_date = datetime.datetime.now()
        today_date = cur_date.strftime('%Y-%m-%d')
        start_time = (cur_date - datetime.timedelta(minutes=2 * settings.FORCE_MEETING_END_TIME)).strftime("%H:%M")
        end_time = (cur_date - datetime.timedelta(minutes=settings.FORCE_MEETING_END_TIME)).strftime("%H:%M")
        return today_date, start_time, end_time

    def _get_cur_day_meeting(self):
        # fix: 当天的mid是否存在重复的可能性？ 一般是不可能，但保险的方式是：结束只执行一次：设置定时器的时间为每15分钟，查询结束的时间是否在结束后15分钟~30分钟之内。
        # resolve: cur_datetime-30 < end_time  < cur_datetime-15
        today_date, start_time, end_time = self._get_today_end_meeting()
        return self.meeting_dao.get_cur_date_meeting(self.community, today_date, start_time, end_time)

    def refresh_meeting_participants(self):
        meetings = self._get_cur_day_meeting()
        for meeting in meetings:
            meeting_info = self.meeting_participants_dao.get(meeting.id)
            if not meeting_info:
                logger.info("start to handle meeting:{}".format(meeting.id))
                meeting_participants = self.meeting_adapter_impl.get_participants(model_to_dict(meeting))
                if meeting_participants.get("participants"):
                    participants = [user["name"] for user in meeting_participants["participants"]]
                    deduplication_participants = list(set(participants))
                    data = {
                        "meeting": meeting,
                        "participants": ",".join(deduplication_participants)
                    }
                    self.meeting_participants_dao.create(**data)

    def force_stop_meeting(self):
        meetings = self._get_cur_day_meeting()
        for meeting in meetings:
            self.meeting_adapter_impl.force_end_meeting(model_to_dict(meeting))


def work_flow(handle_meeting: HandleMeeting):
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
