#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2025/6/19 17:19
# @Author  : Tom_zc
# @FileName: meeting_cache_dao.py
# @Software: PyCharm

from meeting.models import MeetingCache


class MeetingCacheDao:
    dao = MeetingCache

    @classmethod
    def get_by_meeting_id(cls, meeting_id):
        return cls.dao.objects.filter(meeting_id=meeting_id).first()

    @classmethod
    def create(cls, **kwargs):
        return cls.dao.objects.create(**kwargs)
