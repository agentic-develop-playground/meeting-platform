#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.

import logging
import math
import calendar
from datetime import datetime

from django.conf import settings
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from meeting.domain.primitive.cycle_type import CycleType
from meeting.domain.primitive.meeting_status import BusinessMeetingStatus
from meeting.models import Meeting, MeetingObsRecords, MeetingCycleSubMeeting
from meeting.infrastructure.dao.meeting_cycle_sub_dao import MeetingCycleSubMeetingDao
from meeting.infrastructure.dao.meeting_records_bili_dao import MeetingRecordsBiliDao
from meeting.infrastructure.dao.meeting_records_obs_dao import MeetingRecordsObsDao

from meeting.infrastructure.dao.meeting_cycle_dao import MeetingCycleDao
from meeting.infrastructure.dao.meeting_dao import MeetingDao

from meeting_platform.utils.check_params import check_field, check_invalid_content, check_email_list, check_date, \
    check_time, check_link, check_duration, check_email_in_list
from meeting_platform.utils.common import to_anonymous_email_list
from meeting_platform.utils.ret_api import MyValidationError
from meeting_platform.utils.ret_code import RetCode
from meeting_platform.utils.client.audit_client import AuditClient

logger = logging.getLogger("log")


class MeetingListQuerySerializer(serializers.Serializer):
    """会议列表查询参数序列化器

    用于GET请求参数验证，遵循DRF最佳实践
    """
    community = serializers.CharField(required=True)
    date = serializers.CharField(required=False)
    start_date = serializers.CharField(required=False)
    end_date = serializers.CharField(required=False)
    sponsor = serializers.CharField(required=False)
    group_name = serializers.CharField(required=False)
    platform = serializers.CharField(required=False)
    topic = serializers.CharField(required=False)  # 新增：会议名称模糊查询
    status = serializers.IntegerField(required=False, min_value=0, max_value=4)
    include_private = serializers.BooleanField(required=False, default=True)

    # 分页参数
    page = serializers.IntegerField(default=1, min_value=1)
    size = serializers.IntegerField(default=10, min_value=1, max_value=100)

    # 排序参数
    order_by = serializers.ChoiceField(
        choices=['date', 'start', 'end', 'sponsor', 'group_name', 'platform'],
        default='date'
    )
    order_type = serializers.ChoiceField(
        choices=['asc', 'desc'],
        default='desc'
    )

    def validate_community(self, value):
        """验证社区名称"""
        if value not in settings.COMMUNITY_SUPPORT:
            logger.error("community {} is not exist in COMMUNITY_SUPPORT".format(value))
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        return value

    def validate_date(self, value):
        """验证日期格式"""
        if value:
            return check_date(value).strftime('%Y-%m-%d')
        return value

    def validate_start_date(self, value):
        """验证开始日期格式"""
        if value:
            return check_date(value).strftime('%Y-%m-%d')
        return value

    def validate_end_date(self, value):
        """验证结束日期格式"""
        if value:
            return check_date(value).strftime('%Y-%m-%d')
        return value


def calculate_business_status(meeting_data, now=None):
    """计算会议业务状态

    业务状态枚举:
    - 0: 未开始 (当前时间 < 会议开始时间 且 status=0)
    - 1: 进行中 (会议时间段内 且 status=1)
    - 2: 已结束 (当前时间 > 会议结束时间 且 status=2)
    - 3: 超时 (当前时间 > 会议结束时间 且 status=1)
    - 4: 已取消 (is_delete=True)

    Args:
        meeting_data: 包含 date, start, end, status, is_delete 字段的会议数据字典
        now: 当前时间，用于测试时可传入

    Returns:
        int: 业务状态值 (0/1/2/3/4)
    """
    if now is None:
        now = datetime.now()

    # 优先判断已取消（is_delete 为 True/1/'1' 时表示已删除）
    is_delete = meeting_data.get('is_delete')
    if is_delete in [True, 1, '1']:
        return BusinessMeetingStatus.CANCELLED.value

    date = meeting_data.get('date')
    start = meeting_data.get('start')
    end = meeting_data.get('end')
    status = meeting_data.get('status', BusinessMeetingStatus.NOT_STARTED.value)

    if not date or not start or not end:
        return BusinessMeetingStatus.NOT_STARTED.value  # 默认未开始

    try:
        meeting_start_time = datetime.strptime(f"{date} {start}", "%Y-%m-%d %H:%M")
        meeting_end_time = datetime.strptime(f"{date} {end}", "%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        return BusinessMeetingStatus.NOT_STARTED.value

    # 超时：当前时间 > 结束时间 且 status=1 (进行中)
    if now > meeting_end_time and status == BusinessMeetingStatus.ONGOING.value:
        return BusinessMeetingStatus.OVERTIME.value

    # 已结束/已完成：当前时间 > 结束时间 且 status=2
    if now > meeting_end_time and status == BusinessMeetingStatus.ENDED.value:
        return BusinessMeetingStatus.ENDED.value

    # 进行中：时间在会议时间段内 且 status=1
    if meeting_start_time <= now <= meeting_end_time and status == BusinessMeetingStatus.ONGOING.value:
        return BusinessMeetingStatus.ONGOING.value

    # 未开始：当前时间 < 开始时间
    if now < meeting_start_time:
        return BusinessMeetingStatus.NOT_STARTED.value

    # 默认返回数据库状态
    return status


# noinspection PyMethodMayBeStatic
class MeetingSerializer(ModelSerializer):
    """MeetingSerializer for list a meeting and create meeting"""
    __audit_client = AuditClient()
    __cycle_date = MeetingCycleDao()
    __cycle_sub_dao = MeetingCycleSubMeetingDao()
    __obs_dao = MeetingRecordsObsDao()
    __bili_dao = MeetingRecordsBiliDao()

    duration = serializers.SerializerMethodField()
    duration_time = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    cycle_start_date = serializers.CharField(required=False)
    cycle_end_date = serializers.CharField(required=False)
    cycle_start = serializers.CharField(required=False)
    cycle_end = serializers.CharField(required=False)
    cycle_type = serializers.CharField(required=False)
    cycle_interval = serializers.CharField(required=False)
    cycle_point = serializers.CharField(required=False)

    class Meta:
        """Meta Meta"""
        model = Meeting
        fields = ['id', 'sponsor', 'group_name', 'community', 'topic', 'platform', 'date', 'start', 'end',
                  'agenda', 'etherpad', 'email_list', 'mid', 'm_mid', 'join_url', 'create_time', 'update_time',
                  'is_private', 'is_delete', 'is_record', 'duration', 'duration_time', 'is_cycle', 'status',
                  'cycle_start_date', 'cycle_end_date', 'cycle_start', 'cycle_end', 'cycle_type', 'cycle_interval',
                  'cycle_point']
        extra_kwargs = {
            'id': {'read_only': True},
            'mid': {'read_only': True},
            'm_mid': {'read_only': True},
            'join_url': {'read_only': True},
            'create_time': {'read_only': True},
            'update_time': {'read_only': True},
            'is_delete': {'read_only': True},
            'duration': {'read_only': True},
            'duration_time': {'read_only': True},

            'sponsor': {'required': True},
            'group_name': {'required': True},
            'community': {'required': True},
            'topic': {'required': True},
            'platform': {'required': True},
            'is_record': {'required': True},

            'is_private': {'required': False},
            'is_cycle': {'required': False},
            'date': {'required': False},
            'start': {'required': False},
            'end': {'required': False},
            'agenda': {'required': False},
            'etherpad': {'required': False},
            'email_list': {'required': False},
            'cycle_start_date': {'required': False},
            'cycle_end_date': {'required': False},
            'cycle_start': {'required': False},
            'cycle_end': {'required': False},
            'cycle_type': {'required': False},
            'cycle_interval': {'required': False},
            'cycle_point': {'required': False},
        }

    def _check_content_by_audit(self, value):
        if value and not self.__audit_client.check_content_ok(value):
            raise MyValidationError(RetCode.STATUS_INVALID_CONTENT_FAILED)

    def validate_sponsor(self, value):
        """check length of 64"""
        check_field(value, 64)
        check_invalid_content(value)
        return value

    def validate_group_name(self, value):
        """check length of 64"""
        check_field(value, 64)
        check_invalid_content(value)
        self._check_content_by_audit(value)
        return value

    def validate_community(self, value):
        """check community"""
        if value not in settings.COMMUNITY_SUPPORT:
            logger.error("community {} is not exist in COMMUNITY_SUPPORT".format(value))
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        return value

    def validate_topic(self, value):
        """check length of 128，not include \r\n url xss"""
        check_field(value, 128)
        check_invalid_content(value)
        self._check_content_by_audit(value)
        return value

    def validate_platform(self, value):
        """check platform"""
        return value

    def validate_date(self, value):
        """check date"""
        if value:
            value = check_date(value)
            return value.strftime('%Y-%m-%d')

    @staticmethod
    def check_date(value):
        value = check_date(value)
        return value.strftime('%Y-%m-%d')

    @staticmethod
    def check_month(value):
        try:
            year, month = value.split("-")
            _, last_day_num = calendar.monthrange(int(year), int(month))
            first_day = datetime(int(year), int(month), 1).date()
            last_day = datetime(int(year), int(month), last_day_num).date()
            return first_day.strftime('%Y-%m-%d'), last_day.strftime('%Y-%m-%d')
        except Exception as e:
            logger.error("invalid month:{}, and e:{}".format(value, e))
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)

    def validate_start(self, value):
        """check start"""
        if value:
            check_time(value)
            return value

    def validate_end(self, value):
        """check end"""
        if value:
            check_time(value)
            return value

    def validate_is_record(self, value):
        """check record"""
        if not isinstance(value, bool):
            logger.error("invalid is_record:{}".format(value))
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        return value

    def validate_is_private(self, value):
        """check private"""
        if not isinstance(value, bool):
            logger.error("invalid is_private:{}".format(value))
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        return value

    def validate_etherpad(self, value):
        """check etherpad"""
        if value:
            check_link(value)
            return value

    def validate_agenda(self, value):
        """check agenda"""
        if value:
            check_field(value, 4096)
            check_invalid_content(value, check_crlf=False)
            self._check_content_by_audit(value)
            return value

    def validate_email_list(self, value):
        """check email_list"""
        if value:
            check_email_list(value)
            return value

    def validate_is_cycle(self, value):
        """check is_cycle"""
        if not isinstance(value, bool):
            logger.error("invalid is_recycle:{}".format(value))
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        return value

    def validate_cycle_start_date(self, value):
        """check the cycle_start_date"""
        if value:
            check_date(value)
            return value

    def validate_cycle_end_date(self, value):
        """check the cycle_end_date"""
        if value:
            check_date(value)
            return value

    def validate_cycle_start(self, value):
        """check the cycle start"""
        if value:
            check_time(value)
            return value

    def validate_cycle_end(self, value):
        """check the cycle end"""
        if value:
            check_time(value)
            return value

    def validate_cycle_type(self, value):
        """check the cycle type"""
        if value is not None:
            return CycleType.check_value(value)

    def validate_cycle_interval(self, value):
        """check the cycle interval"""
        if value is not None:
            return int(value)

    def validate_cycle_point(self, value):
        """check the cycle point"""
        if value is not None:
            try:
                new_values = list()
                value_list = value.split(",")
                for value_tmp in value_list:
                    new_values.append(int(value_tmp))
                return new_values
            except Exception as e:
                logger.info("invalid cycle_point:{}, e:{}".format(value, e))
                raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)

    def validate(self, attrs):
        if "is_private" not in attrs:
            attrs["is_private"] = False
        if "is_cycle" not in attrs:
            attrs["is_cycle"] = False
        if attrs["is_private"]:
            if attrs["platform"].lower() != "welink":
                logger.error('only wk platform support the private meeting.')
                raise MyValidationError(RetCode.STATUS_MEETING_PRIVATE_SUPPORT_TYPE)
            if attrs["is_cycle"]:
                logger.error('only the not cycle meeting support the private meeting.')
                raise MyValidationError(RetCode.STATUS_MEETING_PRIVATE_SUPPORT_CYCLE)
            if "email_list" in attrs:
                check_email_in_list(attrs["email_list"], settings.COMMUNITY_PRIVATE_MEETING_EMAIL_SUFFIX.get(attrs["community"]))
        if not attrs["is_cycle"]:
            check_duration(attrs["start"], attrs["end"], attrs["date"], datetime.now())
        if attrs["community"] not in settings.COMMUNITY_HOST.keys():
            logger.error('the community of {} have no resources in COMMUNITY_HOST in settings.'
                         .format(attrs["community"]))
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        if attrs["platform"] not in settings.COMMUNITY_HOST[attrs["community"]].keys():
            logger.error('platform {} is not exist in COMMUNITY_HOST.'.format(attrs["platform"]))
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        if attrs["is_cycle"] and attrs["platform"].lower() != "welink":
            logger.error('only wk platform support the cycle meeting.')
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        if attrs["is_cycle"] and attrs["cycle_type"] == CycleType.Month and attrs["cycle_interval"] != 1:
            logger.error('month not support interval not equal one.')
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        if attrs["is_cycle"] and attrs["cycle_type"] == CycleType.Month and len(attrs["cycle_point"]) != 1:
            logger.error('month only support select one day.')
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        return attrs

    def get_duration(self, obj):
        """get duration"""
        if obj.start and obj.end:
            return math.ceil(float(obj.end.replace(':', '.'))) - math.floor(float(obj.start.replace(':', '.')))

    def get_duration_time(self, obj):
        """get duration time"""
        if obj.start and obj.end:
            return obj.start.split(':')[0] + ':00' + '-' + str(math.ceil(float(obj.end.replace(':', '.')))) + ':00'

    def get_status(self, obj):
        """获取业务状态

        数据库 status 已在保存时正确计算，直接返回数据库值
        只需要处理 is_delete=True 时返回已取消状态
        """
        is_delete = obj.is_delete
        if is_delete in [True, 1, '1']:
            return BusinessMeetingStatus.CANCELLED.value
        return obj.status

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["email_list"] = to_anonymous_email_list(data.get("email_list"))
        cycle_date = self.__cycle_date.get_by_mid(instance.mid)
        if cycle_date:
            data["cycle_start_date"] = cycle_date.start_date
            data["cycle_end_date"] = cycle_date.end_date
            data["cycle_start"] = cycle_date.start
            data["cycle_end"] = cycle_date.end
            data["cycle_type"] = cycle_date.cycle_type
            data["cycle_interval"] = cycle_date.interval
            data["cycle_point"] = cycle_date.point.split(",") if cycle_date.point is not None else None
            data["cycle_sub"] = list(self.__cycle_sub_dao.get_by_mid(instance.mid))
        else:
            data["cycle_start_date"] = None
            data["cycle_end_date"] = None
            data["cycle_start"] = None
            data["cycle_end"] = None
            data["cycle_type"] = None
            data["cycle_interval"] = None
            data["cycle_point"] = None
            data["cycle_sub"] = list()
        data["obs_data"] = list(self.__obs_dao.get_by_mid(instance.mid))
        data["bili_data"] = list(self.__bili_dao.get_by_mid(instance.mid))
        return data


# noinspection PyMethodMayBeStatic
class SingleMeetingSerializer(ModelSerializer):
    """UpdateMeetingSerializer for update or delete meeting"""
    __audit_client = AuditClient()
    __cycle_sub_dao = MeetingCycleSubMeetingDao()
    __cycle_date = MeetingCycleDao()
    __obs_dao = MeetingRecordsObsDao()
    __bili_dao = MeetingRecordsBiliDao()

    duration = serializers.SerializerMethodField()
    duration_time = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    is_notify = serializers.BooleanField(required=False)
    cycle_start_date = serializers.CharField(required=False)
    cycle_end_date = serializers.CharField(required=False)
    cycle_start = serializers.CharField(required=False)
    cycle_end = serializers.CharField(required=False)
    cycle_type = serializers.CharField(required=False)
    cycle_interval = serializers.CharField(required=False)
    cycle_point = serializers.CharField(required=False)

    class Meta:
        """Meta Meta"""
        model = Meeting
        fields = ['id', 'sponsor', 'group_name', 'community', 'topic', 'platform', 'date', 'start', 'end',
                  'agenda', 'etherpad', 'email_list', 'mid', 'm_mid', 'is_record', 'duration', 'duration_time',
                  'join_url', 'create_time', 'update_time', 'is_delete', 'is_cycle', 'status',
                  'cycle_start_date',
                  'cycle_end_date', 'cycle_start', 'cycle_end', 'cycle_type', 'cycle_interval', 'cycle_point',
                  'is_notify', 'is_private']
        extra_kwargs = {
            'id': {'read_only': True},
            'sponsor': {'read_only': True},
            'group_name': {'read_only': True},
            'community': {'read_only': True},
            'platform': {'read_only': True},
            'mid': {'read_only': True},
            'm_mid': {'read_only': True},
            'join_url': {'read_only': True},
            'create_time': {'read_only': True},
            'update_time': {'read_only': True},
            'is_delete': {'read_only': True},
            'duration': {'read_only': True},
            'duration_time': {'read_only': True},

            'topic': {'required': True},
            'is_record': {'required': True},

            'is_private': {'required': False},
            'is_cycle': {'required': False},
            'date': {'required': False},
            'start': {'required': False},
            'end': {'required': False},
            'agenda': {'required': False},
            'etherpad': {'required': False},
        }

    def _check_content_by_audit(self, value):
        if value and not self.__audit_client.check_content_ok(value):
            raise MyValidationError(RetCode.STATUS_INVALID_CONTENT_FAILED)

    def validate_topic(self, value):
        """check length of 128，not include \r\n url xss"""
        check_field(value, 128)
        check_invalid_content(value)
        self._check_content_by_audit(value)
        return value

    def validate_email_list(self, value):
        """check email_list"""
        if value:
            check_email_list(value)
            return value

    def validate_date(self, value):
        """check date"""
        if value is not None:
            value = check_date(value)
            return value.strftime('%Y-%m-%d')

    def validate_start(self, value):
        """check start"""
        if value is not None:
            check_time(value)
            return value

    def validate_end(self, value):
        """check end"""
        if value is not None:
            check_time(value)
            return value

    def validate_agenda(self, value):
        """check agenda"""
        if value:
            check_field(value, 4096)
            check_invalid_content(value, check_crlf=False)
            self._check_content_by_audit(value)
            return value

    def validate_etherpad(self, value):
        """check etherpad"""
        if value:
            check_link(value)
            return value

    def validate_is_record(self, value):
        """check record"""
        if not isinstance(value, bool):
            logger.error("invalid is_record:{}".format(value))
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        return value

    def validate_is_private(self, value):
        """check private"""
        if not isinstance(value, bool):
            logger.error("invalid is_private:{}".format(value))
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        return value

    def validate_is_cycle(self, value):
        """check is_cycle"""
        if not isinstance(value, bool):
            logger.error("invalid is_cycle:{}".format(value))
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        return value

    def validate_cycle_start_date(self, value):
        """check the cycle_start_date"""
        if value:
            check_date(value)
            return value

    def validate_cycle_end_date(self, value):
        """check the cycle_end_date"""
        if value:
            check_date(value)
            return value

    def validate_cycle_start(self, value):
        """check the cycle start"""
        if value:
            check_time(value)
            return value

    def validate_cycle_end(self, value):
        """check the cycle end"""
        if value:
            check_time(value)
            return value

    def validate_cycle_type(self, value):
        """check the cycle type"""
        if value is not None:
            return CycleType.check_value(value)

    def validate_cycle_interval(self, value):
        """check the cycle interval"""
        if value is not None:
            return int(value)

    def validate_cycle_point(self, value):
        """check the cycle point"""
        if value is not None:
            try:
                new_values = list()
                value_list = value.split(",")
                for value_tmp in value_list:
                    new_values.append(int(value_tmp))
                return new_values
            except Exception as e:
                logger.info("invalid cycle_point:{}, e:{}".format(value, e))
                raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)

    def validate(self, attrs):
        """all validate data"""
        if "is_cycle" not in attrs:
            attrs["is_cycle"] = False
        if not attrs["is_cycle"]:
            check_duration(attrs["start"], attrs["end"], attrs["date"], datetime.now())
        attrs["update_time"] = datetime.now()
        if "is_private" not in attrs:
            attrs["is_private"] = False
        if attrs["is_private"]:
            # Get platform from instance if not in attrs (platform is read_only in update)
            platform = attrs.get("platform")
            if platform is None and self.instance:
                platform = self.instance.platform
            if platform and platform.lower() != "welink":
                logger.error('only wk platform support the private meeting.')
                raise MyValidationError(RetCode.STATUS_MEETING_PRIVATE_SUPPORT_TYPE)
            if attrs["is_cycle"]:
                logger.error('only the not cycle meeting support the private meeting.')
                raise MyValidationError(RetCode.STATUS_MEETING_PRIVATE_SUPPORT_CYCLE)
            if "email_list" in attrs:
                # Get community from instance if not in attrs (community is read_only in update)
                community = attrs.get("community")
                if community is None and self.instance:
                    community = self.instance.community
                check_email_in_list(attrs["email_list"], settings.COMMUNITY_PRIVATE_MEETING_EMAIL_SUFFIX.get(community))
        return attrs

    def get_duration(self, obj):
        """get duration"""
        if obj.start and obj.end:
            return math.ceil(float(obj.end.replace(':', '.'))) - math.floor(float(obj.start.replace(':', '.')))

    def get_duration_time(self, obj):
        """get duration time"""
        if obj.start and obj.end:
            return obj.start.split(':')[0] + ':00' + '-' + str(math.ceil(float(obj.end.replace(':', '.')))) + ':00'

    def get_status(self, obj):
        """获取业务状态

        数据库 status 已在保存时正确计算，直接返回数据库值
        只需要处理 is_delete=True 时返回已取消状态
        """
        is_delete = obj.is_delete
        if is_delete in [True, 1, '1']:
            return BusinessMeetingStatus.CANCELLED.value
        return obj.status

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["email_list"] = data.get("email_list")
        cycle_date = self.__cycle_date.get_by_mid(instance.mid)
        if cycle_date:
            data["cycle_start_date"] = cycle_date.start_date
            data["cycle_end_date"] = cycle_date.end_date
            data["cycle_start"] = cycle_date.start
            data["cycle_end"] = cycle_date.end
            data["cycle_type"] = cycle_date.cycle_type
            data["cycle_interval"] = cycle_date.interval
            data["cycle_point"] = cycle_date.point.split(",") if cycle_date.point is not None else None
            data["cycle_sub"] = list(self.__cycle_sub_dao.get_by_mid(instance.mid))
        else:
            data["cycle_start_date"] = None
            data["cycle_end_date"] = None
            data["cycle_start"] = None
            data["cycle_end"] = None
            data["cycle_type"] = None
            data["cycle_interval"] = None
            data["cycle_point"] = None
            data["cycle_sub"] = list()
        data["obs_data"] = list(self.__obs_dao.get_by_mid(instance.mid))
        data["bili_data"] = list(self.__bili_dao.get_by_mid(instance.mid))
        return data


# noinspection PyMethodMayBeStatic
class CycleSubMeetingSerializer(ModelSerializer):
    """UpdateMeetingSerializer for update or delete meeting"""
    __cycle_sub_dao = MeetingCycleSubMeetingDao()
    __meeting_dao = MeetingDao()

    is_notify = serializers.BooleanField(required=False)
    is_record = serializers.SerializerMethodField()
    cycle_sub = serializers.SerializerMethodField()
    sponsor = serializers.SerializerMethodField()

    class Meta:
        model = MeetingCycleSubMeeting
        fields = ['mid', 'sub_id', 'date', 'start', 'end', "is_record", "cycle_sub", "sponsor", "is_notify"]
        extra_kwargs = {
            'sub_id': {'read_only': True},
            'is_record': {'read_only': True},
            'cycle_sub': {'read_only': True},
            'sponsor': {'read_only': True},

            'mid': {'required': True},
            'date': {'required': True},
            'start': {'required': True},
            'end': {'required': True},
        }

    def get_is_record(self, obj):
        meeting_info = self.__meeting_dao.get_by_mid(obj.mid)
        if meeting_info:
            return meeting_info.is_record

    def get_cycle_sub(self, obj):
        """get cycle point"""
        return list(self.__cycle_sub_dao.get_by_mid(obj.mid))

    def get_sponsor(self, obj):
        meeting_info = self.__meeting_dao.get_by_mid(obj.mid)
        if meeting_info:
            return meeting_info.sponsor


class MeetingGroupNameSerializer(ModelSerializer):

    class Meta:
        """Meta Meta"""
        model = Meeting
        fields = ['group_name']
        extra_kwargs = {
            'group_name': {'read_only': True},
        }

# noinspection PyMethodMayBeStatic
class TranslateVideoTextSerializer(ModelSerializer):
    class Meta:
        model = MeetingObsRecords
        fields = ['mid', 'sub_id', 'text_vtt_url', 'text_json_url', 'topic_url']

    def validate_mid(self, value):
        if not value:
            logger.error("check the empty mid")
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        return value

    def validate_text_vtt_url(self, value):
        if not value:
            logger.error("check the empty text_vtt_url")
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        return value

    def validate_text_json_url(self, value):
        if not value:
            logger.error("check the empty text_json_url")
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        return value

    def validate_sub_id(self, value):
        return value

    def validate_topic_url(self, value):
        return value


class MeetingListSerializer(serializers.Serializer):
    """会议列表序列化器（合并周期和非周期会议）

    返回字段:
    - id: 会议ID（周期会议为父会议ID）
    - topic: 会议主题
    - sponsor: 发起人
    - group_name: SIG名称
    - community: 社区
    - platform: 平台
    - date: 会议日期
    - start: 开始时间
    - end: 结束时间
    - status: 业务状态（0=未开始, 1=进行中, 2=已结束, 3=超时, 4=已取消）
    - is_cycle: 是否周期会议
    - sub_id: 子会议ID（周期会议有值）
    - mid: 会议ID
    - agenda: 会议议程
    - etherpad: 协作文档链接
    - join_url: 会议链接
    - cycle_start_date: 周期会议开始日期（仅周期会议）
    - cycle_end_date: 周期会议结束日期（仅周期会议）
    - cycle_start: 周期会议开始时间（仅周期会议）
    - cycle_end: 周期会议结束时间（仅周期会议）
    - cycle_type: 周期类型（仅周期会议）
    - cycle_interval: 周期间隔（仅周期会议）
    - cycle_point: 周期点位（仅周期会议）
    """
    id = serializers.IntegerField()
    topic = serializers.CharField()
    sponsor = serializers.CharField()
    group_name = serializers.CharField()
    community = serializers.CharField()
    platform = serializers.CharField()
    date = serializers.CharField()
    start = serializers.CharField()
    end = serializers.CharField()
    status = serializers.SerializerMethodField()
    is_cycle = serializers.BooleanField(default=False)
    sub_id = serializers.CharField(allow_null=True, default=None)
    mid = serializers.CharField()
    agenda = serializers.CharField(allow_null=True, default=None)
    etherpad = serializers.CharField(allow_null=True, default=None)
    join_url = serializers.CharField(allow_null=True, default=None)
    cycle_start_date = serializers.CharField(allow_null=True, default=None)
    cycle_end_date = serializers.CharField(allow_null=True, default=None)
    cycle_start = serializers.CharField(allow_null=True, default=None)
    cycle_end = serializers.CharField(allow_null=True, default=None)
    cycle_type = serializers.IntegerField(allow_null=True, default=None)
    cycle_interval = serializers.IntegerField(allow_null=True, default=None)
    cycle_point = serializers.ListField(allow_null=True, default=None)

    def get_status(self, obj):
        """获取业务状态

        数据库 status 已在保存时正确计算，直接返回数据库值
        只需要处理 is_delete=True 时返回已取消状态
        """
        is_delete = obj.get('is_delete')
        if is_delete in [True, 1, '1']:
            return BusinessMeetingStatus.CANCELLED.value
        return obj.get('status')

