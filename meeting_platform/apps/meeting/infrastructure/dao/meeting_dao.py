#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2024/8/16 14:45
# @Author  : Tom_zc
# @FileName: meeting_adapter.py
# @Software: PyCharm
from meeting.models import Meeting
from django.db.models import Q


class MeetingDao:
    dao = Meeting

    @classmethod
    def get_conflict_meeting(cls, community, platform, date, start_search, end_search, meeting_id=None):
        if meeting_id is None:
            return cls.dao.objects.filter(community=community, platform=platform, is_delete=0,
                                          date=date, end__gt=start_search, start__lt=end_search)
        return cls.dao.objects.filter(community=community, platform=platform, is_delete=0,
                                      date=date, end__gt=start_search, start__lt=end_search).exclude(id=meeting_id)

    @classmethod
    def get_today_meeting_counts(cls, community, sponsor, date):
        return cls.dao.objects.filter(community=community, sponsor=sponsor, create_time__date=date).count()

    @classmethod
    def get_queryset(cls):
        return cls.dao.objects.all()

    @classmethod
    def create(cls, **kwargs):
        return cls.dao.objects.create(**kwargs)

    @classmethod
    def get_by_id(cls, meeting_id):
        return cls.dao.objects.filter(id=meeting_id, is_delete=0).first()

    @classmethod
    def update_by_id(cls, meeting_id, **kwargs):
        return cls.dao.objects.filter(id=meeting_id, is_delete=0).update(**kwargs)

    @classmethod
    def delete_by_id(cls, meeting_id):
        return cls.dao.objects.filter(id=meeting_id, is_delete=0).update(is_delete=1)

    @classmethod
    def get_uploaded_mid_by_community_and_status(cls, community, status):
        return cls.dao.objects.filter(is_delete=0, community=community, is_record=True, upload_status=status) \
            .values_list('mid', flat=True)

    @classmethod
    def update_upload_status_by_community_and_mid(cls, community, mid, status):
        return cls.dao.objects.filter(is_delete=0, community=community, is_record=True).filter(mid__in=mid). \
            update(upload_status=status)

    @classmethod
    def get_upload_all_by_community_and_status(cls, community, status, start_date, end_date):
        return cls.dao.objects.filter(is_delete=0, community=community, is_record=True, upload_status=status) \
            .filter(Q(date__gt=start_date) & Q(date__lte=end_date)).all()
