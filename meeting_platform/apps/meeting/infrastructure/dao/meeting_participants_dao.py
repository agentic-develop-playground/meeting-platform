#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2025/3/18 21:09
# @Author  : Tom_zc
# @FileName: meeting_participants_dao.py
# @Software: PyCharm

from meeting.models import MeetingParticipants


class MeetingParticipantsDao:
    dao = MeetingParticipants

    @classmethod
    def create(cls, **kwargs):
        return cls.dao.objects.create(**kwargs)

    @classmethod
    def get(cls, meeting_id):
        return cls.dao.objects.filter(meeting__id=meeting_id).first()
