#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.

from meeting.models import MeetingParticipants


class MeetingParticipantsDao:
    dao = MeetingParticipants

    @classmethod
    def create(cls, **kwargs):
        return cls.dao.objects.create(**kwargs)

    @classmethod
    def get(cls, meeting_id):
        return cls.dao.objects.filter(meeting__id=meeting_id).first()
