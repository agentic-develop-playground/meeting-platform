#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.

from meeting.models import MeetingCache


class MeetingCacheDao:
    dao = MeetingCache

    @classmethod
    def get_by_meeting_id(cls, meeting_id):
        return cls.dao.objects.filter(meeting_id=meeting_id).first()

    @classmethod
    def create(cls, **kwargs):
        return cls.dao.objects.create(**kwargs)
