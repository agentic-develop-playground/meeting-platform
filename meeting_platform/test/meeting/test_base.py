#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
import logging
import uuid
import base64

from rest_framework.test import APITestCase

from meeting.models import Meeting, User

logger = logging.getLogger("log")


class CommonClass:
    meeting_dao = Meeting
    user_dao = User

    def create_user(self):
        uuid_str = str(uuid.uuid4())
        new_uuid_str = uuid_str.replace("-", "")
        username = "test_{}".format(new_uuid_str)
        user = self.user_dao.objects.create_superuser(username, None, username)
        return user

    def get_all_user(self):
        return self.user_dao.objects.all()

    def get_user_by_id(self, user_id):
        return self.user_dao.objects.filter(id=user_id).first()

    def get_users_by_username(self, username):
        return self.user_dao.objects.filter(sponsor=username).first()

    def clear_user(self):
        ret = self.meeting_dao.objects.all().delete()
        logger.info("delete user and result is:{}".format(str(ret)))

    def create_meeting(self, **kwargs):
        return self.meeting_dao.objects.create(**kwargs)

    def get_meeting_by_username(self, username):
        return self.meeting_dao.objects.filter(sponsor=username).first()

    def get_meetings(self):
        return self.meeting_dao.objects.all()

    def get_meetings_by_username(self, username):
        return self.meeting_dao.objects.filter(sponsor=username).all()

    def clear_meetings(self):
        ret = self.meeting_dao.objects.all().delete()
        logger.info("delete meeting and result is:{}".format(str(ret)))

    def format_token(self, token):
        return "basic {}".format(str(token))

    # noinspection PyUnresolvedReferences
    def enable_client_auth(self, username):
        data = "{}:{}".format(username, username)
        base64_str = base64.b64encode(data.encode()).decode("utf-8")
        self.client.credentials(HTTP_AUTHORIZATION=self.format_token(base64_str))


class TestCommonMeeting(CommonClass, APITestCase):
    pass
