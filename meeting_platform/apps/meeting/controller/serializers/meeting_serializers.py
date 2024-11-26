#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2024/8/16 17:08
# @Author  : Tom_zc
# @FileName: meeting_serializers.py
# @Software: PyCharm

import logging
import math
from datetime import datetime

from django.conf import settings
from rest_framework import serializers
from rest_framework.serializers import ModelSerializer

from meeting_platform.utils.check_params import check_field, check_invalid_content, check_email_list, check_date, \
    check_time, check_link, check_duration
from meeting_platform.utils.common import mask_email_full
from meeting_platform.utils.ret_api import MyValidationError
from meeting_platform.utils.ret_code import RetCode

from meeting.models import Meeting

logger = logging.getLogger("log")


class MeetingSerializer(ModelSerializer):
    """MeetingSerializer for get a meeting and create meeting"""

    duration = serializers.SerializerMethodField()
    duration_time = serializers.SerializerMethodField()
    email_list = serializers.SerializerMethodField()

    class Meta:
        """Meta Meta"""
        model = Meeting
        fields = ['id', 'sponsor', 'group_name', 'community', 'topic', 'platform', 'date', 'start', 'end',
                  'agenda', 'etherpad', 'email_list', 'mid', 'm_mid', 'is_record', 'upload_status',
                  'join_url', 'replay_url', 'create_time', 'update_time', 'is_delete', 'duration', 'duration_time']
        extra_kwargs = {
            'id': {'read_only': True},
            'sponsor': {'required': True},
            'group_name': {'required': True},
            'community': {'required': True},
            'topic': {'required': True},
            'platform': {'required': True},
            'date': {'required': True},
            'start': {'required': True},
            'end': {'required': True},
            'agenda': {'required': False},
            'etherpad': {'required': False},
            'email_list': {'required': False},
            'is_record': {'required': True},
            'mid': {'read_only': True},
            'm_mid': {'read_only': True},
            'upload_status': {'read_only': True},
            'join_url': {'read_only': True},
            'replay_url': {'read_only': True},
            'create_time': {'read_only': True},
            'update_time': {'read_only': True},
            'is_delete': {'read_only': True},
            'duration': {'read_only': True},
            'duration_time': {'read_only': True},
        }

    def validate_sponsor(self, value):
        """check length of 64"""
        check_field(value, 64)
        check_invalid_content(value)
        return value

    def validate_group_name(self, value):
        """check length of 64"""
        check_field(value, 64)
        check_invalid_content(value)
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
        return value

    def validate_platform(self, value):
        """check platform"""
        return value

    def validate_date(self, value):
        """check date"""
        value = check_date(value)
        return value.strftime('%Y-%m-%d')

    @staticmethod
    def check_date(value):
        value = check_date(value)
        return value.strftime('%Y-%m-%d')

    def validate_start(self, value):
        """check start"""
        check_time(value)
        return value

    def validate_end(self, value):
        """check end"""
        check_time(value)
        return value

    def validate_is_record(self, value):
        """check record"""
        if not isinstance(value, bool):
            logger.error("invalid is_record:{}".format(value))
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
            return value

    def validate_email_list(self, value):
        """check email_list"""
        if value:
            check_email_list(value)
            return value

    def validate(self, attrs):
        etherpad = attrs.get("etherpad")
        if etherpad is not None and not etherpad.startswith(settings.COMMUNITY_ETHERPAD[attrs["community"]]):
            logger.error("invalid etherpad:{}".format(etherpad))
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        check_duration(attrs["start"], attrs["end"], attrs["date"], datetime.now())
        if attrs["platform"] not in settings.COMMUNITY_HOST[attrs["community"]].keys():
            logger.error('platform {} is not exist in COMMUNITY_HOST.'.format(attrs["platform"]))
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        return attrs

    def get_duration(self, obj):
        """get duration"""
        return math.ceil(float(obj.end.replace(':', '.'))) - math.floor(float(obj.start.replace(':', '.')))

    def get_duration_time(self, obj):
        """get duration time"""
        return obj.start.split(':')[0] + ':00' + '-' + str(math.ceil(float(obj.end.replace(':', '.')))) + ':00'

    def get_email_list(self, obj):
        """get email list"""
        email_list = obj.email_list
        if email_list:
            email_strs = email_list.split(";")
            desensitization_email = [mask_email_full(email) for email in email_strs]
            return ";".join(desensitization_email)
        return email_list


class SingleMeetingSerializer(ModelSerializer):
    """UpdateMeetingSerializer for update meeting"""
    duration = serializers.SerializerMethodField()
    duration_time = serializers.SerializerMethodField()
    email_list = serializers.SerializerMethodField()

    class Meta:
        """Meta Meta"""
        model = Meeting
        fields = ['id', 'sponsor', 'group_name', 'community', 'topic', 'platform', 'date', 'start', 'end',
                  'agenda', 'etherpad', 'email_list', 'mid', 'm_mid', 'is_record', 'upload_status',
                  'join_url', 'replay_url', 'create_time', 'update_time', 'is_delete', 'duration', 'duration_time']
        extra_kwargs = {
            'id': {'read_only': True},
            'sponsor': {'read_only': True},
            'group_name': {'read_only': True},
            'community': {'read_only': True},
            'platform': {'read_only': True},
            'topic': {'required': True},
            'date': {'required': True},
            'start': {'required': True},
            'end': {'required': True},
            'agenda': {'required': False},
            'etherpad': {'required': False},
            'is_record': {'required': True},
            'email_list': {'read_only': True},
            'mid': {'read_only': True},
            'm_mid': {'read_only': True},
            'upload_status': {'read_only': True},
            'join_url': {'read_only': True},
            'replay_url': {'read_only': True},
            'create_time': {'read_only': True},
            'update_time': {'read_only': True},
            'is_delete': {'read_only': True},
            'duration': {'read_only': True},
            'duration_time': {'read_only': True},
        }

    def validate_topic(self, value):
        """check length of 128，not include \r\n url xss"""
        check_field(value, 128)
        check_invalid_content(value)
        return value

    def validate_date(self, value):
        """check date"""
        value = check_date(value)
        return value.strftime('%Y-%m-%d')

    def validate_start(self, value):
        """check start"""
        check_time(value)
        return value

    def validate_end(self, value):
        """check end"""
        check_time(value)
        return value

    def validate_agenda(self, value):
        """check agenda"""
        if value:
            check_field(value, 4096)
            check_invalid_content(value, check_crlf=False)
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

    def validate(self, attrs):
        """all validate data"""
        check_duration(attrs["start"], attrs["end"], attrs["date"], datetime.now())
        attrs["update_time"] = datetime.now()
        return attrs

    def get_duration(self, obj):
        """get duration"""
        return math.ceil(float(obj.end.replace(':', '.'))) - math.floor(float(obj.start.replace(':', '.')))

    def get_duration_time(self, obj):
        """get duration time"""
        return obj.start.split(':')[0] + ':00' + '-' + str(math.ceil(float(obj.end.replace(':', '.')))) + ':00'

    def get_email_list(self, obj):
        """get email list"""
        email_list = obj.email_list
        if email_list:
            email_strs = email_list.split(";")
            desensitization_email = [mask_email_full(email) for email in email_strs]
            return ";".join(desensitization_email)
        return email_list
