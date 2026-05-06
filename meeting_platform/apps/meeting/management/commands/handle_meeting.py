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

from meeting.application.meeting import MeetingApp
from meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl import MeetingAdapterImpl
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
    _meeting_app = MeetingApp()
    _meeting_participants_dao = meeting_participants_dao.MeetingParticipantsDao
    _meeting_cycle_sub_dao = meeting_cycle_sub_dao.MeetingCycleSubMeetingDao
    meeting_adapter_impl = MeetingAdapterImpl()

    def __init__(self, community):
        self.community = community

    @staticmethod
    def _get_windows_meeting():
        cur_date = datetime.datetime.now()
        today_date = cur_date.strftime('%Y-%m-%d')
        start_time = (cur_date - datetime.timedelta(minutes=settings.FORCE_MEETING_END_TIME)).strftime("%H:%M")
        end_time = (cur_date - datetime.timedelta(minutes=(settings.FORCE_MEETING_END_TIME - 15))).strftime("%H:%M")
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
        now = datetime.datetime.now()
        today = now.strftime('%Y-%m-%d')
        yesterday = (now - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        now_time = now.strftime('%H:%M')
        for meeting in meetings:
            try:
                if meeting.is_cycle:
                    # 昨天的子会议：无条件结束
                    sub = self._meeting_cycle_sub_dao.get_by_mid_date(meeting.mid, yesterday)
                    if sub:
                        self._meeting_app.force_stop_meeting(meeting.id, sub.sub_id)
                    # 今天的子会议：仅当 end <= now_time 时才结束
                    sub = self._meeting_cycle_sub_dao.get_by_mid_date(meeting.mid, today)
                    if sub and sub.end <= now_time:
                        self._meeting_app.force_stop_meeting(meeting.id, sub.sub_id)
                else:
                    self._meeting_app.force_stop_meeting(meeting.id, None)
            except Exception as e:
                logger.error("[handle_meeting] force_stop_meeting id:{} error:{}, traceback:{}".format(
                    meeting.id, str(e), traceback.format_exc()))


def work_flow(handle_meeting: HandleMeeting):
    try:
        if settings.CRONJOB_FORCE_END_MEETING:
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
