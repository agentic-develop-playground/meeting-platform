#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.

from meeting.models import MeetingCycleDate


class MeetingCycleDao:
    _dao = MeetingCycleDate

    @classmethod
    def get_by_id(cls, cycle_id):
        return cls._dao.objects.filter(id=cycle_id).first()

    @classmethod
    def get_by_mid(cls, cycle_mid):
        return cls._dao.objects.filter(mid=cycle_mid).first()

    @classmethod
    def get_by_mid_and_info(cls, mid_list, start_date, end_date, start, end, cycle_type):
        return cls._dao.objects.filter(mid__in=mid_list,
                                       start_date=start_date,
                                       end_date=end_date,
                                       start=start,
                                       end=end,
                                       cycle_type=cycle_type).count()

    @classmethod
    def create(cls, **kwargs):
        return cls._dao.objects.create(**kwargs)

    @classmethod
    def update(cls, mid, **kwargs):
        return cls._dao.objects.filter(mid=mid).update(**kwargs)

    @classmethod
    def get_all(cls):
        return cls._dao.objects.all()
