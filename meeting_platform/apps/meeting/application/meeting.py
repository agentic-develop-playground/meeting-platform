#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
import datetime
import logging
import secrets
import traceback

from django.conf import settings
from django.utils import timezone
from django.forms import model_to_dict
from django.db.models import Q
from django.db import transaction

from meeting.domain.primitive.upload_status import UploadStatus
from meeting.domain.primitive.time_range import TimeRange
from meeting.domain.primitive.cycle_type import CycleType
from meeting.domain.primitive.meeting_status import BusinessMeetingStatus
from meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl import MeetingAdapterImpl
from meeting.infrastructure.adapter.message_adapter_impl.email_adapter_impl import CreateMessageEmailAdapterImpl, \
    DeleteMessageEmailAdapterImpl, UpdateMessageEmailAdapterImpl, DeleteSubMessageEmailAdapterImpl, \
    UpdateSubMessageEmailAdapterImpl
from meeting.infrastructure.adapter.message_adapter_impl.kafka_adapter_impl import CreateMessageKafKaAdapterImpl, \
    DeleteMessageKafKaAdapterImpl, UpdateMessageKafKaAdapterImpl
from meeting.infrastructure.dao import meeting_dao, meeting_participants_dao
from meeting.infrastructure.dao.meeting_records_obs_dao import MeetingRecordsObsDao
from meeting.infrastructure.dao.meeting_records_bili_dao import MeetingRecordsBiliDao
from meeting.infrastructure.dao.meeting_cycle_dao import MeetingCycleDao
from meeting.infrastructure.dao.meeting_cycle_sub_dao import MeetingCycleSubMeetingDao
from meeting.infrastructure.code_adapter.core_operators import get_cycle_date_by_policy

from meeting_platform.utils.common import start_thread
from meeting_platform.utils.operation_log import set_log_thread_local, log_key
from meeting_platform.utils.ret_api import MyValidationError
from meeting_platform.utils.ret_code import RetCode

logger = logging.getLogger("log")


class MeetingApp:
    meeting_dao = meeting_dao.MeetingDao
    meeting_cycle_dao = MeetingCycleDao
    meeting_cycle_sub_dao = MeetingCycleSubMeetingDao
    meeting_obs_records_dao = MeetingRecordsObsDao
    meeting_bili_records_dao = MeetingRecordsBiliDao
    meeting_participants_dao = meeting_participants_dao.MeetingParticipantsDao
    meeting_adapter_impl = MeetingAdapterImpl()
    create_message_adapter_impl = [CreateMessageEmailAdapterImpl, CreateMessageKafKaAdapterImpl]
    update_message_adapter_impl = [UpdateMessageEmailAdapterImpl, UpdateMessageKafKaAdapterImpl]
    update_sub_message_adapter_impl = [UpdateSubMessageEmailAdapterImpl, UpdateMessageKafKaAdapterImpl]
    delete_message_adapter_impl = [DeleteMessageEmailAdapterImpl, DeleteMessageKafKaAdapterImpl]
    delete_sub_message_adapter_impl = [DeleteSubMessageEmailAdapterImpl, DeleteMessageKafKaAdapterImpl]

    def _get_and_check_conflict_meetings_by_date(self, meeting, meeting_id=None, check_single_meeting=False):
        """check the conflict the meeting, if not conflict and return meeting"""
        unavailable_host_ids = list()
        conflict_topics = list()
        meeting_date_list = list()
        cur_day_host_ids = list()
        community = meeting["community"]
        platform = meeting["platform"]

        if not meeting["is_cycle"] or check_single_meeting:
            meeting_date_list.append({"date": meeting["date"], "start": meeting["start"], "end": meeting["end"]})
        else:
            meeting_date_list = get_cycle_date_by_policy(meeting)
            if len(meeting_date_list) == 0:
                logger.info("[MeetingApp/_get_and_check_conflict_meetings_by_date] no meeting date in the date range")
                raise MyValidationError(RetCode.STATUS_MEETING_DATE_NOT_IN_RANGE_FAILED)
        logger.info("get the date list:{}".format(meeting_date_list))
        for cycle_date in meeting_date_list:
            start_search = datetime.datetime.strftime(
                (datetime.datetime.strptime(cycle_date["start"], '%H:%M') - datetime.timedelta(minutes=30)),
                '%H:%M')
            end_search = datetime.datetime.strftime(
                (datetime.datetime.strptime(cycle_date["end"], '%H:%M') + datetime.timedelta(minutes=30)),
                '%H:%M')
            # 会议的mid
            unavailable_host_id, conflict_topic, cur_day_host_id = self.meeting_dao.get_conflict_meeting(community, platform, cycle_date["date"],
                                                                                                         start_search, end_search, meeting_id)
            if meeting.get("host_id") is not None and meeting["host_id"] in unavailable_host_id:
                logger.info('[MeetingApp/_get_and_check_conflict_meetings_by_date] '
                            '{}/{}: update find the conflict host:{}, and conflict with: {}'.format(
                    meeting["community"], meeting["platform"], meeting["host_id"], ",".join(list(set(conflict_topics)))))
                raise MyValidationError(RetCode.STATUS_MEETING_DATE_CONFLICT)
            unavailable_host_ids.extend(unavailable_host_id)
            conflict_topics.extend(conflict_topic)
            cur_day_host_ids.extend(cur_day_host_id)
        logger.info("unavailable_host_ids host id:{}".format(",".join(unavailable_host_ids)))
        # get the all host
        host_info = settings.COMMUNITY_HOST[meeting["community"]][meeting["platform"]]
        host_list = [key["HOST"] for key in host_info]
        available_host_id = list(set(host_list) - set(unavailable_host_ids))
        if len(available_host_id) == 0:
            logger.info('[MeetingApp/_get_and_check_conflict_meetings_by_date] '
                        '{}/{}: no available host, and conflict with:{}'.format(
                meeting["community"], meeting["platform"], ",".join(list(set(conflict_topics)))))
            raise MyValidationError(RetCode.STATUS_MEETING_DATE_CONFLICT)
        # 排除当天有会议的host_ids, 优先选择当天没有会议的
        preferred_choice = list(set(available_host_id) - set(cur_day_host_ids))
        if len(preferred_choice) > 0:
            return secrets.choice(preferred_choice)
        return secrets.choice(available_host_id)

    @staticmethod
    def _check_cycle_end(meeting):
        """check the end date lt 180"""
        if meeting["is_cycle"]:
            cur_date = datetime.datetime.now()
            end_date = datetime.datetime.strptime(meeting["cycle_end_date"], "%Y-%m-%d")
            if end_date >= cur_date + datetime.timedelta(days=180):
                logger.error("_check_cycle_end must create the meeting lt 180 days")
                raise MyValidationError(RetCode.STATUS_MEETING_IN_HALF_YEAR_FAILED)

    @staticmethod
    def _send_message(meeting, message_handler):
        """send the message"""
        for handler in message_handler:
            try:
                handler().send_message(meeting)
            except Exception as e:
                logger.error("[MeetingApp/_send_message] err:{}, and traceback:{}".format(e, traceback.format_exc()))

    def __get_meeting_sub_count(self, mid):
        """get the meeting cycle sub meeting count"""
        m_count = self.meeting_cycle_sub_dao.get_counts_by_mid(mid)
        if m_count <= 1:
            logger.error("sub meeting count lt 1")
            raise MyValidationError(RetCode.STATUS_MEETING_CANNOT_DELETE_FAILED)

    def _calc_meeting_count(self, meeting):
        """calc the meeting count"""
        # TODO add the lock to avoid the concurrent
        today = timezone.now().date()
        meeting_counts = self.meeting_dao.get_today_meeting_counts(meeting["community"], meeting["sponsor"], today)
        if meeting_counts >= settings.MEETING_CREATE_COUNT:
            raise MyValidationError(RetCode.STATUS_MEETING_CREATE_COUNT_LIMIT)

    def _check_recurring_meetings(self, meeting):
        """check recurring meeting"""
        if not meeting["is_cycle"]:
            m_count = self.meeting_dao.get_repeat_meeting_by_community_sponsor_date_start_counts(meeting["community"],
                                                                                                 meeting["group_name"],
                                                                                                 meeting["sponsor"],
                                                                                                 meeting["date"],
                                                                                                 meeting["start"])
        else:
            mid = self.meeting_dao.get_repeat_meeting_by_cycle_mid(meeting["community"],
                                                                   meeting["group_name"],
                                                                   meeting["sponsor"])
            m_count = self.meeting_cycle_dao.get_by_mid_and_info(mid,
                                                                 meeting["cycle_start_date"],
                                                                 meeting["cycle_end_date"],
                                                                 meeting["cycle_start"],
                                                                 meeting["cycle_end"],
                                                                 meeting["cycle_type"].value)
        if m_count != 0:
            raise MyValidationError(RetCode.STATUS_MEETING_REPEAT_FAILED)

    @staticmethod
    def _get_create_meeting_po(meeting):
        """get the meeting po"""
        return {
            "sponsor": meeting.get("sponsor"),
            "group_name": meeting.get("group_name"),
            "community": meeting.get("community"),
            "topic": meeting.get("topic"),
            "platform": meeting.get("platform"),
            "is_cycle": meeting.get("is_cycle"),
            "date": meeting.get("date"),
            "start": meeting.get("start"),
            "end": meeting.get("end"),
            "agenda": meeting.get("agenda"),
            "etherpad": meeting.get("etherpad"),
            "email_list": meeting.get("email_list"),
            "host_id": meeting.get("host_id"),
            "mid": meeting.get("mid"),
            "m_mid": meeting.get("m_mid"),
            "join_url": meeting.get("join_url"),
            "is_record": meeting.get("is_record"),
            "is_private": meeting.get("is_private"),
        }

    @staticmethod
    def _get_create_meeting_cycle_sub_po(meeting, sub_meeting, meeting_obj):
        """get the meeting cycle sub po"""
        return {
            "mid": meeting["mid"],
            "sub_id": sub_meeting["sub_id"],
            "date": sub_meeting["date"],
            "start": sub_meeting["start"],
            "end": sub_meeting["end"],
            "meeting": meeting_obj,
        }

    @staticmethod
    def _get_create_meeting_cycle_date_po(meeting, meeting_obj):
        """get the meeting cycle date po"""
        return {
            "mid": meeting["mid"],
            "start_date": meeting.get("cycle_start_date"),
            "end_date": meeting.get("cycle_end_date"),
            "start": meeting.get("cycle_start"),
            "end": meeting.get("cycle_end"),
            "cycle_type": meeting.get("cycle_type").value,
            "interval": meeting.get("cycle_interval"),
            "meeting": meeting_obj,
            "point": ",".join([str(i) for i in meeting["cycle_point"]])
            if meeting.get("cycle_point") is not None else None,
        }

    def _create_obs_records(self, status, mid, sub_id, meeting_id):
        """create obs records"""
        if settings.IS_UPLOAD_OBS:
            self.meeting_obs_records_dao.create(status, mid, sub_id, meeting_id)

    def _create_bili_records(self, status, mid, sub_id, meeting_id):
        """create obs records"""
        if settings.IS_UPLOAD_BILI:
            self.meeting_bili_records_dao.create(status, mid, sub_id, meeting_id)

    def _delete_obs_records(self, mid, sub_id):
        """create obs records"""
        if settings.IS_UPLOAD_OBS:
            self.meeting_obs_records_dao.delete_by_mid_and_sub_id(mid, sub_id)

    def _delete_bili_records(self, mid, sub_id):
        """create obs records"""
        if settings.IS_UPLOAD_BILI:
            self.meeting_bili_records_dao.delete_by_mid_and_sub_id(mid, sub_id)

    def _save_dao(self, meeting):
        """save to database"""
        with transaction.atomic():
            meeting_data = self._get_create_meeting_po(meeting)
            meeting_obj = self.meeting_dao.create(**meeting_data)
            if meeting["is_cycle"]:
                for sub_meeting in meeting.get("sub_info"):
                    cycle_sub_meeting = self._get_create_meeting_cycle_sub_po(meeting, sub_meeting, meeting_obj)
                    self.meeting_cycle_sub_dao.create(**cycle_sub_meeting)
                    self._create_obs_records(UploadStatus.INIT.value,
                                             meeting["mid"],
                                             sub_meeting["sub_id"],
                                             meeting_obj.id)
                    self._create_bili_records(UploadStatus.INIT.value,
                                              meeting["mid"],
                                              sub_meeting["sub_id"],
                                              meeting_obj.id)
                cycle_date = self._get_create_meeting_cycle_date_po(meeting, meeting_obj)
                self.meeting_cycle_dao.create(**cycle_date)
            else:
                self._create_obs_records(UploadStatus.INIT.value,
                                         meeting["mid"],
                                         None,
                                         meeting_obj.id)
                self._create_bili_records(UploadStatus.INIT.value,
                                          meeting["mid"],
                                          None,
                                          meeting_obj.id)
            return meeting_obj.id

    def _update_dao(self, meeting_id, meeting):
        """update the meeting dao"""
        with transaction.atomic():
            if meeting["is_cycle"]:
                # clear the data
                cur_datetime = datetime.datetime.now()
                cur_date_str = cur_datetime.date().strftime("%Y-%m-%d")
                cur_time_str = cur_datetime.time().strftime("%H:%M")
                cycle_sub_info = self.meeting_cycle_sub_dao.get_by_mid_and_date(meeting["mid"],
                                                                                cur_date_str,
                                                                                cur_time_str)
                for cycle_sub_temp in cycle_sub_info:
                    self._delete_obs_records(cycle_sub_temp.mid, cycle_sub_temp.sub_id)
                    self._delete_bili_records(cycle_sub_temp.mid, cycle_sub_temp.sub_id)
                self.meeting_cycle_sub_dao.delete_by_mid(meeting["mid"], cur_date_str, cur_time_str)
                # create the sub info
                meeting_obj = self.meeting_dao.get_by_mid(meeting["mid"])
                for sub_meeting in meeting.get("sub_info"):
                    cycle_sub_meeting = self._get_create_meeting_cycle_sub_po(meeting, sub_meeting, meeting_obj)
                    self.meeting_cycle_sub_dao.create(**cycle_sub_meeting)
                    self._create_obs_records(UploadStatus.INIT.value,
                                             meeting["mid"],
                                             sub_meeting["sub_id"],
                                             meeting_obj.id)
                    self._create_bili_records(UploadStatus.INIT.value,
                                              meeting["mid"],
                                              sub_meeting["sub_id"],
                                              meeting_obj.id)
                # create the cycle date info
                cycle_date = self._get_create_meeting_cycle_date_po(meeting, meeting_obj)
                if self.meeting_cycle_dao.get_by_id(meeting["mid"]) is not None:
                    meeting["cycle_date"] = self.meeting_cycle_dao.create(**cycle_date)
                else:
                    del cycle_date["mid"]
                    self.meeting_cycle_dao.update(meeting["mid"], **cycle_date)
            return self.meeting_dao.update_by_id(meeting_id,
                                                 topic=meeting["topic"],
                                                 agenda=meeting["agenda"],
                                                 email_list=meeting["email_list"],
                                                 is_record=meeting["is_record"],
                                                 is_cycle=meeting["is_cycle"],
                                                 date=meeting["date"],
                                                 start=meeting["start"],
                                                 end=meeting["end"],
                                                 sequence=meeting["sequence"],
                                                 )

    def _delete_dao(self, meeting_id, meeting):
        with transaction.atomic():
            self.meeting_dao.delete_by_id(meeting_id, meeting["sequence"])
            self.meeting_bili_records_dao.delete_by_mid(meeting["mid"])
            self.meeting_obs_records_dao.delete_by_mid(meeting["mid"])
            if meeting["is_cycle"]:
                self.meeting_cycle_sub_dao.update_status_by_mid(meeting["mid"], BusinessMeetingStatus.CANCELLED.value)
        return meeting_id

    def _update_sub_dao(self, meeting):
        with transaction.atomic():
            self.meeting_cycle_sub_dao.update_by_mid_and_sub_id(meeting["mid"],
                                                                meeting["sub_id"],
                                                                date=meeting["date"],
                                                                start=meeting["start"],
                                                                end=meeting["end"])
            result = self.meeting_dao.update_by_id(meeting["id"], sequence=meeting["sequence"])
            return result

    def _delete_sub_dao(self, mid, sub_id, meeting):
        with transaction.atomic():
            self.meeting_cycle_sub_dao.delete_by_mid_and_sub_id(mid, sub_id)
            result = self.meeting_dao.update_by_id(meeting["id"], sequence=meeting["sequence"])
            return result

    def create(self, meeting):
        """create meeting"""
        # check the meeting limit
        self._calc_meeting_count(meeting)
        # check the recurring meetings
        self._check_recurring_meetings(meeting)
        # check the cycle end
        self._check_cycle_end(meeting)
        # check meeting-conflict
        meeting["host_id"] = self._get_and_check_conflict_meetings_by_date(meeting)
        # create meeting
        meeting_info = self.meeting_adapter_impl.create(meeting["host_id"], meeting)
        meeting.update(meeting_info)
        # create in database
        result_id = self._save_dao(meeting)
        meeting["id"] = result_id
        # send message
        if meeting.get("is_cycle"):
            meeting["date"] = meeting["sub_info"][0]["date"]
            meeting["start"] = meeting["sub_info"][0]["start"]
            meeting["end"] = meeting["sub_info"][0]["end"]
        start_thread(self._send_message, (meeting, self.create_message_adapter_impl))
        logger.info('[MeetingApp/create] {}/{}: create meeting which mid is {} and id is {}.'.
                    format(meeting["community"], meeting["platform"], meeting["mid"], result_id))
        return meeting["id"]

    def update(self, request, meeting_id, meeting_data):
        """update meeting"""
        meeting = self.meeting_dao.get_by_id(meeting_id)
        if not meeting:
            logger.error('[MeetingApp/update]meeting id:{} is not exist'.format(meeting_id))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        if meeting.email_list:
            email_list = meeting.email_list.split(";")
        else:
            email_list = []
        meeting = model_to_dict(meeting)
        set_log_thread_local(request, log_key, [meeting["community"], meeting["topic"], meeting_id])
        meeting.update(meeting_data)
        meeting.update({"sequence": meeting["sequence"] + 1})
        # Check is_private platform validation
        if meeting.get("is_private"):
            if meeting.get("platform", "").lower() != "welink":
                logger.error('only welink platform support the private meeting.')
                raise MyValidationError(RetCode.STATUS_MEETING_PRIVATE_SUPPORT_TYPE)
        # check modify meeting count
        if meeting["sequence"] > settings.MEETING_MODIFY_COUNT + 1:
            raise MyValidationError(RetCode.STATUS_MEETING_MODIFY_COUNT_LIMIT)
        # check the cycle end
        self._check_cycle_end(meeting)
        # check meeting-conflict
        self._get_and_check_conflict_meetings_by_date(meeting, meeting_id)
        # update meeting
        resp = self.meeting_adapter_impl.update(meeting)
        meeting.update(resp)
        # update in database
        result = self._update_dao(meeting_id, meeting)
        # send message
        if meeting.get("is_cycle"):
            meeting["date"] = meeting["sub_info"][0]["date"]
            meeting["start"] = meeting["sub_info"][0]["start"]
            meeting["end"] = meeting["sub_info"][0]["end"]
        if meeting.get("is_notify"):
            if meeting_data.get("email_list") is not None:
                email_list.extend(meeting_data["email_list"].split(";"))
            meeting["email_list"] = ",".join(list(set(email_list)))
            start_thread(self._send_message, (meeting, self.update_message_adapter_impl))
        logger.info('[MeetingApp/update] {}/{}: update meeting which mid is {} and id is {}.'
                    .format(meeting["community"], meeting["platform"], meeting["mid"], meeting["id"]))
        return result

    def delete(self, request, meeting_id):
        """delete meeting"""
        meeting = self.meeting_dao.get_by_id(meeting_id)
        if not meeting:
            logger.error('[MeetingApp/delete]Invalid meeting id:{}'.format(meeting_id))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        meeting = model_to_dict(meeting)
        set_log_thread_local(request, log_key, [meeting["community"], meeting["topic"], meeting_id])
        meeting.update({"sequence": meeting["sequence"] + 1})
        if meeting["is_cycle"]:
            meeting_cycle_obj = self.meeting_cycle_dao.get_by_mid(meeting["mid"])
            dict_data = {
                "cycle_start_date": meeting_cycle_obj.start_date,
                "cycle_end_date": meeting_cycle_obj.end_date,
                "cycle_start": meeting_cycle_obj.start,
                "cycle_end": meeting_cycle_obj.end,
                "cycle_type": CycleType(meeting_cycle_obj.cycle_type),
                "cycle_interval": meeting_cycle_obj.interval,
                "cycle_point": meeting_cycle_obj.point,
            }
            meeting.update(dict_data)
        # check not delete in the before in start date
        # delete meeting
        self.meeting_adapter_impl.delete(meeting)
        # update is_delete=1 in database
        result = self._delete_dao(meeting_id, meeting)
        # send message
        start_thread(self._send_message, (meeting, self.delete_message_adapter_impl))
        logger.info('[MeetingApp/delete] {}/{}: delete meeting which mid is {} and id is {}.'
                    .format(meeting["community"], meeting["platform"], meeting["mid"], meeting_id))
        return result

    def update_sub(self, meeting_data):
        meeting = self.meeting_dao.get_by_mid(meeting_data["mid"])
        if not meeting:
            logger.error('[MeetingApp/update_sub]Invalid meeting mid:{}'.format(meeting_data["mid"]))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        meeting_sub_obj = self.meeting_cycle_sub_dao.get_by_mid_and_sub_id(meeting_data["mid"], meeting_data["sub_id"])
        if not meeting_sub_obj:
            logger.error('[MeetingApp/update_sub]Invalid meeting mid:{}/{}'.format(meeting_data["mid"],
                                                                                   meeting_data["sub_id"]))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        meeting = model_to_dict(meeting)
        meeting.update({"sequence": meeting["sequence"] + 1})
        meeting.update(meeting_data)
        # check modify meeting count
        if meeting["sequence"] > settings.MEETING_MODIFY_COUNT + 1:
            raise MyValidationError(RetCode.STATUS_MEETING_MODIFY_COUNT_LIMIT)
        # check meeting-conflict
        self._get_and_check_conflict_meetings_by_date(meeting, meeting["id"], check_single_meeting=True)
        # update meeting
        self.meeting_adapter_impl.update_sub(meeting)
        # update in database
        result = self._update_sub_dao(meeting)
        # send message
        meeting["check_single_meeting"] = True
        if meeting.get("is_cycle"):
            start_thread(self._send_message, (meeting, self.update_sub_message_adapter_impl))
        logger.info('[MeetingApp/update] {}/{}: update meeting which mid is {} and id is {}.'
                    .format(meeting["community"], meeting["platform"], meeting["mid"], meeting["id"]))
        return result

    def delete_sub(self, sub_id):
        """delete sub meeting"""
        sub_info = self.meeting_cycle_sub_dao.get_by_sub_id(sub_id)
        if sub_info is None:
            logger.error('[MeetingApp/delete_sub]Invalid meeting sub id:{}'.format(sub_id))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        mid = sub_info.mid
        meeting = self.meeting_dao.get_by_mid(mid)
        if not meeting:
            logger.error('[MeetingApp/delete_sub]Invalid meeting id:{}'.format(meeting["id"]))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        meeting_sub_info = self.meeting_cycle_sub_dao.get_by_mid_and_sub_id(mid, sub_id)
        if not meeting_sub_info:
            logger.error('[MeetingApp/delete_sub]Invalid meeting mid/sub id:{}/{}'.format(mid, sub_id))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        meeting = model_to_dict(meeting)
        meeting.update({"sequence": meeting["sequence"] + 1})
        meeting.update(model_to_dict(sub_info))
        # check the current sub meeting count lt 1
        self.__get_meeting_sub_count(meeting["mid"])
        # delete meeting
        self.meeting_adapter_impl.delete_sub(meeting)
        # update is_delete=1 in database
        result = self._delete_sub_dao(mid, sub_id, meeting)
        # send message
        meeting["check_single_meeting"] = True
        start_thread(self._send_message, (meeting, self.delete_sub_message_adapter_impl))
        logger.info('[MeetingApp/delete_sub] {}/{}: delete meeting which mid is {} and id is {}.'
                    .format(meeting["community"], meeting["platform"], meeting["mid"], meeting["id"]))
        return result

    def notify_meeting(self, meeting_id):
        """send the message and email by meeting_id"""
        meeting = self.meeting_dao.get_by_id(meeting_id)
        if not meeting:
            logger.error('[MeetingApp/notify_meeting]meeting id:{} is not exist'.format(meeting_id))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)

        meeting = model_to_dict(meeting)
        if meeting.get("is_cycle"):
            meeting_cycle_obj = self.meeting_cycle_dao.get_by_mid(meeting["mid"])
            meeting_cycle_info = model_to_dict(meeting_cycle_obj)
            meeting_cycle_info["cycle_interval"] = meeting_cycle_info["interval"]
            meeting_cycle_info["cycle_type"] = CycleType.check_value(meeting_cycle_info["cycle_type"])
            meeting.update(meeting_cycle_info)
            meeting["sub_info"] = list(self.meeting_cycle_sub_dao.get_by_mid(meeting["mid"]))
            meeting["cycle_start"] = meeting_cycle_info["start"]
            meeting["cycle_end"] = meeting_cycle_info["end"]
            meeting["cycle_start_date"] = meeting_cycle_info["start_date"]
            meeting["cycle_end_date"] = meeting_cycle_info["end_date"]
        start_thread(self._send_message, (meeting, self.create_message_adapter_impl))

    def get_participants(self, meeting_id):
        """get participants"""
        meeting = self.meeting_dao.get_by_id(meeting_id)
        if not meeting:
            logger.error('[MeetingApp/get_participants]Invalid meeting id:{}'.format(meeting_id))
            raise MyValidationError(RetCode.INFORMATION_CHANGE_ERROR)
        meeting_participants = self.meeting_participants_dao.get(meeting_id)
        if meeting_participants:
            return meeting_participants.participants.split(",")
        return list()

    @staticmethod
    def get_meeting_platform(community):
        """get platform"""
        if community not in settings.COMMUNITY_HOST.keys():
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        host_info = settings.COMMUNITY_HOST.get(community)
        if host_info is not None:
            return list(host_info.keys())
        return list()

    def get_meeting_date(self, community, group_name, date, is_record):
        queryset = self.meeting_dao.get_queryset().filter(is_delete=0, is_private=False)
        if community is not None:
            queryset = queryset.filter(community=community)
        if group_name is not None:
            queryset = queryset.filter(group_name=group_name)
        if is_record is not None:
            queryset = queryset.filter(is_record=is_record)
        if date is None:
            date = datetime.datetime.now()
        else:
            date = datetime.datetime.strptime(date, "%Y-%m-%d")
        show_date_range = 6 * 7
        start_date = (date - datetime.timedelta(days=show_date_range)).strftime('%Y-%m-%d')
        end_date = (date + datetime.timedelta(days=show_date_range)).strftime('%Y-%m-%d')
        queryset_date = queryset.filter(Q(date__gte=start_date, date__lte=end_date) | Q(
            cycle_sub_meeting__date__gte=start_date, cycle_sub_meeting__date__lte=end_date,
        )).distinct().order_by('-date', 'id').values("mid", "date")
        deduplication_date = set()
        for date in queryset_date:
            if date["date"] is not None:
                deduplication_date.add(date["date"])
            else:
                all_date = self.meeting_cycle_sub_dao.get_by_date_range(start_date, end_date, date["mid"])
                deduplication_date = deduplication_date.union(all_date)
        sort_date = sorted(deduplication_date)
        return list(sort_date)

    def get_meeting_group_name(self, community):
        queryset = self.meeting_dao.get_meeting_group_name(community)
        return list(queryset)

    def get_meeting_sponsors(self, community, sponsor_keyword=None):
        """获取会议发起者列表（支持分页）

        Args:
            community: 社区名称
            sponsor_keyword: 发起者名称模糊查询关键词

        Returns:
            dict: [...]
        """
        queryset = self.meeting_dao.get_meeting_sponsors(community, sponsor_keyword)
        return list(queryset)

    def force_stop_meeting(self, meeting_id,sub_id):
        queryset = self.meeting_dao.get_queryset().filter(is_delete=0)
        meeting = queryset.filter(id=meeting_id).first()
        if not meeting:
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)

        meeting_adapter = MeetingAdapterImpl()
        meeting_dict = model_to_dict(meeting)
        if sub_id:
            # 强制结束周期子会议
            sub_meeting = MeetingCycleSubMeetingDao.get_all().filter(sub_id=sub_id).first()
            if not sub_meeting:
                raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)

            meeting_dict["sub_id"] = sub_id
            meeting_adapter.force_end_meeting(meeting_dict)

            # 清除子会议状态（标记为已结束）
            MeetingCycleSubMeetingDao.clear_status(sub_id)
        else:
            # 强制结束非周期会议
            meeting_adapter.force_end_meeting(meeting_dict)

            if meeting.is_cycle:
                # 周期会议：清除所有正在进行中的子会议的状态
                sub_meetings = MeetingCycleSubMeetingDao.get_by_mid(meeting.mid)
                for sub in sub_meetings:
                    if sub.get('status') == BusinessMeetingStatus.ONGOING.value:  # 进行中
                        MeetingCycleSubMeetingDao.clear_status(sub.get('sub_id'))
            else:
                # 非周期会议
                self.meeting_dao.clear_status(meeting_id)
        return True

    @staticmethod
    def get_time_range_meeting(queryset, time_range):
        time_range_domain = TimeRange.check_value(time_range)
        cur_date = datetime.datetime.now()
        weekly_start_date = str(cur_date - datetime.timedelta(days=7))[:10]
        weekly_end_date = str(cur_date + datetime.timedelta(days=7))[:10]
        recently_date = cur_date.strftime('%Y-%m-%d')
        daily_date = str(cur_date)[:10]
        after_weekly_start_date = cur_date.strftime('%Y-%m-%d')
        after_weekly_end_date = str(cur_date + datetime.timedelta(days=7))[:10]

        queryset_data = {
            TimeRange.WEEKLY.value: queryset.filter((Q(date__gte=weekly_start_date, date__lte=weekly_end_date) |
                                                     Q(cycle_sub_meeting__date__gte=weekly_start_date,
                                                       cycle_sub_meeting__date__lte=weekly_end_date))),
            TimeRange.RECENTLY.value: queryset.filter(Q(date__gte=recently_date) |
                                                      Q(cycle_sub_meeting__date__gte=recently_date)),
            TimeRange.DAILY.value: queryset.filter(Q(date=daily_date) | Q(cycle_sub_meeting__date=daily_date)),
            TimeRange.AFTER_WEEKLY.value: queryset.filter((Q(date__gte=after_weekly_start_date,
                                                             date__lte=after_weekly_end_date) |
                                                           Q(
                                                               cycle_sub_meeting__date__gte=after_weekly_start_date,
                                                               cycle_sub_meeting__date__lte=after_weekly_end_date
                                                           ))),
        }
        return queryset_data.get(time_range_domain.value)

    def get_merged_meeting_list(self, community, filters, order_by='date', order_type='asc', page=1, page_size=10):
        """获取合并后的会议列表（展开周期子会议）

        Args:
            community: 社区名称（必填）
            filters: 筛选条件字典
            order_by: 排序字段
            order_type: 排序方式（asc/desc）
            page: 页码
            page_size: 每页数量

        Returns:
            dict: {'total': total, 'list': [...], 'page': page, 'page_size': page_size}
        """
        # 验证并修正参数
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 10

        valid_order_fields = ['date', 'start', 'end', 'sponsor', 'group_name', 'platform']
        if order_by not in valid_order_fields:
            order_by = 'date'

        # 获取非周期会议QuerySet
        non_cycle_qs = self.meeting_dao.get_non_cycle_meetings(community, filters)

        # 获取周期子会议QuerySet
        cycle_sub_qs = self.meeting_cycle_sub_dao.get_expanded_sub_meetings_queryset(community, filters)

        # 使用union合并两个查询
        # 注意：union后的QuerySet不能再进行filter，但可以进行order_by和切片
        merged_qs = non_cycle_qs.union(cycle_sub_qs)

        # 计算总数（在union后计算）
        total = len(merged_qs)

        # 构建排序
        if order_type == 'desc':
            order_field = f'-{order_by}'
        else:
            order_field = order_by

        # 排序并分页
        # 注意：union后的QuerySet排序需要使用相同的字段名
        offset = (page - 1) * page_size
        merged_qs = merged_qs.order_by(order_field, 'start')[offset:offset + page_size]

        # 返回字典列表
        meeting_list = list(merged_qs)

        # 批量获取周期会议的 MeetingCycleDate（避免 N+1 查询）
        cycle_mid = [m['mid'] for m in meeting_list if m.get('is_cycle')]
        if cycle_mid:
            cycle_dates = MeetingCycleDao.get_by_mids(cycle_mid)
            cycle_date_map = {cd.mid: cd for cd in cycle_dates}

            for m in meeting_list:
                if m.get('is_cycle'):
                    cd = cycle_date_map.get(m['mid'])
                    if cd:
                        m['cycle_start_date'] = cd.start_date
                        m['cycle_end_date'] = cd.end_date
                        m['cycle_start'] = cd.start
                        m['cycle_end'] = cd.end
                        m['cycle_type'] = cd.cycle_type
                        m['cycle_interval'] = cd.interval
                        m['cycle_point'] = cd.point.split(',') if cd.point else None

        return {
            'total': total,
            'list': meeting_list,
            'page': page,
            'size': page_size
        }
