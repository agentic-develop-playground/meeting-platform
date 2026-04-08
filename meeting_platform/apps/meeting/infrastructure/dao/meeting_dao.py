#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
from meeting.models import Meeting
from django.db.models import Q


class MeetingDao:
    dao = Meeting

    @classmethod
    def get_conflict_meeting(cls, community, platform, date, start_search, end_search, meeting_id=None):
        query_set = cls.dao.objects.filter(community=community,
                                           platform=platform,
                                           is_delete=0)
        conflict_query_set = query_set.filter(Q(cycle_sub_meeting__date=date,
                                                cycle_sub_meeting__start__lt=end_search,
                                                cycle_sub_meeting__end__gt=start_search) |
                                              Q(date=date, start__lt=end_search, end__gt=start_search))
        cur_query_set = query_set.filter(Q(cycle_sub_meeting__date=date) | Q(date=date))
        if meeting_id is None:
            return (conflict_query_set.values_list("host_id", flat=True),
                    conflict_query_set.values_list("topic", flat=True),
                    cur_query_set.values_list("host_id", flat=True))
        return (conflict_query_set.exclude(id=meeting_id).values_list("host_id", flat=True),
                conflict_query_set.exclude(id=meeting_id).values_list("topic", flat=True),
                cur_query_set.values_list("host_id", flat=True))

    @classmethod
    def get_today_meeting_counts(cls, community, sponsor, date):
        return cls.dao.objects.filter(community=community, sponsor=sponsor, create_time__date=date).count()

    @classmethod
    def get_repeat_meeting_by_community_sponsor_date_start_counts(cls, community, group_name, sponsor, date, start):
        return cls.dao.objects.filter(community=community, group_name=group_name, sponsor=sponsor,
                                      date=date, start=start, is_delete=False, is_cycle=False).count()

    @classmethod
    def get_repeat_meeting_by_cycle_mid(cls, community, group_name, sponsor):
        return cls.dao.objects.filter(community=community, group_name=group_name, sponsor=sponsor,
                                      is_delete=False, is_cycle=True).values_list("mid", flat=True)

    @classmethod
    def get_queryset(cls):
        return cls.dao.objects.all()

    @classmethod
    def get_meeting_group_name(cls, community):
        return cls.dao.objects.filter(community=community, is_delete=0).order_by("group_name").values_list("group_name", flat=True).distinct()

    @classmethod
    def create(cls, **kwargs):
        return cls.dao.objects.create(**kwargs)

    @classmethod
    def get_by_id(cls, meeting_id):
        return cls.dao.objects.filter(id=meeting_id, is_delete=0).first()

    @classmethod
    def get_by_mid(cls, mid):
        return cls.dao.objects.filter(mid=mid, is_delete=0).first()

    @classmethod
    def get_by_mid_list(cls, mid_list):
        return cls.dao.objects.filter(mid__in=mid_list, is_delete=0).values()

    @classmethod
    def update_by_id(cls, meeting_id, **kwargs):
        return cls.dao.objects.filter(id=meeting_id, is_delete=0).update(**kwargs)

    @classmethod
    def delete_by_id(cls, meeting_id, sequence):
        return cls.dao.objects.filter(id=meeting_id, is_delete=0).update(is_delete=1,
                                                                         sequence=sequence)

    @classmethod
    def get_windows_meeting(cls, community, cur_date, start_time, end_time):
        query_set = cls.dao.objects.filter(community=community, is_delete=0)
        return query_set.filter(Q(cycle_sub_meeting__date=cur_date, cycle_sub_meeting__end__gte= start_time, cycle_sub_meeting__end__lt=end_time) |
                                Q(date=cur_date, end__gte=start_time, end__lt=end_time)).all()

    @classmethod
    def get_point_meeting(cls, community, start_date, end_date):
        return cls.dao.objects.filter(community=community, is_delete=0). \
            filter(Q(date__gte=start_date, date__lt=end_date) | Q(cycle_sub_meeting__date__gte=start_date,
                                                                  cycle_sub_meeting__date__lt=end_date)).all()

    @classmethod
    def get_meeting_by_date(cls, community, start_date, end_date, end_time):
        start_and_end_date = Q(date__gt=start_date, date__lt=end_date)
        today = Q(date=end_date, end__lt=end_time)
        return cls.dao.objects.filter(is_delete=0, community=community). \
            filter().filter(start_and_end_date | today).all()

    @classmethod
    def get_meeting_by_obs_records(cls, community, obs_records, start_date, end_date):
        return cls.dao.objects.filter(is_delete=0, community=community,
                                      is_record=True, id__in=obs_records). \
            filter(Q(date__gt=start_date, date__lte=end_date) | Q(cycle_sub_meeting__date__gt=start_date,
                                                                  cycle_sub_meeting__date__lte=end_date)).all()

    @classmethod
    def get_meeting_by_bili_records(cls, community, bili_records, start_date, end_date):
        return cls.dao.objects.filter(is_delete=0, community=community,
                                      is_record=True, id__in=bili_records). \
            filter(Q(date__gt=start_date, date__lte=end_date) | Q(cycle_sub_meeting__date__gt=start_date,
                                                                  cycle_sub_meeting__date__lte=end_date)).all()
