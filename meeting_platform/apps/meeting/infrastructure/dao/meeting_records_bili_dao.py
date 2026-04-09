#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.

from meeting.models import MeetingBiliRecords


class MeetingRecordsBiliDao:
    _dao = MeetingBiliRecords

    @classmethod
    def get_records_by_status(cls, status):
        return cls._dao.objects.filter(status=status)

    @classmethod
    def get_by_mid(cls, mid):
        return cls._dao.objects.filter(mid=mid).values()

    @classmethod
    def get_by_mid_and_sub_id(cls, mid, sub_id):
        return cls._dao.objects.filter(mid=mid, sub_id=sub_id).values()

    @classmethod
    def get_by_id(cls, cur_id):
        return cls._dao.objects.filter(id=cur_id)

    @classmethod
    def update_records(cls, record_id, **kwargs):
        return cls._dao.objects.filter(id=record_id).update(**kwargs)

    @classmethod
    def create(cls, status, mid, sub_id, meeting_id):
        return cls._dao.objects.create(status=status, mid=mid, sub_id=sub_id, meeting_id=meeting_id)

    @classmethod
    def delete_by_mid_and_sub_id(cls, mid, sub_id):
        return cls._dao.objects.filter(mid=mid, sub_id=sub_id).all().delete()

    @classmethod
    def delete_by_mid(cls, mid):
        return cls._dao.objects.filter(mid=mid).all().delete()

    @classmethod
    def update_by_mid(cls, mid, sub_id, status, **kwargs):
        queryset = cls._dao.objects.filter(mid=mid)
        if sub_id:
            queryset = queryset.filter(sub_id=sub_id)
        return queryset.update(status=status, **kwargs)
