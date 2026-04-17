#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
from meeting.models import Meeting
from django.db.models import Q, Value, CharField
from datetime import datetime, timedelta
from meeting.domain.primitive.meeting_status import BusinessMeetingStatus

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
        return cls.dao.objects.filter(community=community, is_delete=0, is_private=False).order_by("group_name").values_list("group_name", flat=True).distinct()

    @classmethod
    def get_meeting_sponsors(cls, community, sponsor_keyword=None):
        """获取会议发起者列表

        Args:
            community: 社区名称
            sponsor_keyword: 发起者名称模糊查询关键词（可选）

        Returns:
            QuerySet: 发起者名称列表（去重、排序）
        """
        query_set = cls.dao.objects.filter(
            community=community
        )

        # 发起者名称模糊查询
        if sponsor_keyword:
            query_set = query_set.filter(sponsor__icontains=sponsor_keyword)

        return query_set.order_by("sponsor").values_list("sponsor", flat=True).distinct()

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
                                                                         status=BusinessMeetingStatus.CANCELLED.value,
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

    @classmethod
    def get_status_sync_candidates(cls, community, now):
        """获取大于等于今天所有需要同步状态的会议

        新逻辑：查询大于等于今天的所有会议，不再使用时间窗口过滤
        """

        today = now.strftime('%Y-%m-%d')

        query_set = cls.dao.objects.filter(community=community, is_delete=0)

        # 非周期会议：大于等于今天所有会议
        non_cycle_meetings = query_set.filter(is_cycle=False, date__gte=today).all()

        # 周期会议：大于等于今天有子会议的
        cycle_meetings = query_set.filter(
            is_cycle=True,
            cycle_sub_meeting__date__gte=today
        ).distinct().all()

        # 合并结果，去重
        meeting_ids = set()
        result = []
        for m in non_cycle_meetings:
            if m.id not in meeting_ids:
                meeting_ids.add(m.id)
                result.append(m)
        for m in cycle_meetings:
            if m.id not in meeting_ids:
                meeting_ids.add(m.id)
                result.append(m)

        return result

    @classmethod
    def update_status(cls, meeting_id, status):
        """更新会议状态"""
        return cls.dao.objects.filter(id=meeting_id).update(
            status=status,
            status_updated_at=datetime.now()
        )

    @classmethod
    def clear_status(cls, meeting_id):
        """清除会议状态（会议结束时调用）"""
        return cls.dao.objects.filter(id=meeting_id).update(
            status=BusinessMeetingStatus.ENDED.value,
            status_updated_at=datetime.now(),
            warning_email_sent=False
        )

    @classmethod
    def get_upcoming_end_meetings(cls, community, today, warning_minutes=10):
        """获取即将结束的会议（用于发送预警邮件）

        条件：date=今天 AND end在当前时间到当前时间+warning_minutes之间 AND status in [1,3] AND warning_email_sent=False
        """
        now = datetime.now()
        current_time = now.strftime('%H:%M')
        warning_time = (now + timedelta(minutes=warning_minutes)).strftime('%H:%M')

        return cls.dao.objects.filter(
            community=community,
            is_delete=0,
            is_cycle=False,
            date=today,
            end__gte=current_time,
            end__lte=warning_time,
            status__in=[BusinessMeetingStatus.ONGOING.value, BusinessMeetingStatus.OVERTIME.value],
            warning_email_sent=False
        ).all()

    @classmethod
    def has_subsequent_meetings(cls, community, host_id, today, current_end_time):
        """检查当天该host_id是否有后续会议

        Args:
            community: 社区
            host_id: 会议主持人邮箱
            today: 今天日期
            current_end_time: 当前会议结束时间

        Returns:
            bool: 是否有后续会议
        """
        return cls.dao.objects.filter(
            community=community,
            host_id=host_id,
            is_delete=0,
            is_cycle=False,
            date=today,
            start__gt=current_end_time  # 开始时间 > 当前会议结束时间
        ).exists()

    @classmethod
    def get_ongoing_meetings_for_warning(cls, community, today):
        """获取当天所有需要预警检查的会议（进行中/超时且未发送预警）

        注意：不再限制结束时间窗口，由业务逻辑动态判断预警时机
        """

        now = datetime.now()
        current_time = now.strftime('%H:%M')

        return cls.dao.objects.filter(
            community=community,
            is_delete=0,
            is_cycle=False,
            date=today,
            end__gte=current_time,  # 结束时间 >= 当前时间（会议未结束）
            status__in=[BusinessMeetingStatus.ONGOING.value, BusinessMeetingStatus.OVERTIME.value],
            warning_email_sent=False
        ).all()

    @classmethod
    def get_next_meeting_start_time(cls, community, host_id, today, current_end_time):
        """获取当天该host_id的下一场会议的开始时间

        Args:
            community: 社区
            host_id: 会议主持人邮箱
            today: 今天日期
            current_end_time: 当前会议结束时间

        Returns:
            str: 下一场会议的开始时间 (HH:MM)，如果没有后续会议返回 None
        """
        next_meeting = cls.dao.objects.filter(
            community=community,
            host_id=host_id,
            is_delete=0,
            is_cycle=False,
            date=today,
            start__gt=current_end_time
        ).order_by('start').first()

        if next_meeting:
            return next_meeting.start
        return None

    @classmethod
    def mark_warning_email_sent(cls, meeting_id):
        """标记已发送预警邮件"""
        return cls.dao.objects.filter(id=meeting_id).update(warning_email_sent=True)

    @classmethod
    def reset_warning_email_status(cls, meeting_id):
        """重置预警邮件状态（会议开始时调用）"""
        return cls.dao.objects.filter(id=meeting_id).update(warning_email_sent=False)

    @classmethod
    def get_non_cycle_meetings(cls, community, filters):
        """获取非周期会议列表（用于合并会议列表接口）

        返回ValuesQuerySet，字段与周期子会议一致，便于UNION合并
        """
        query_set = cls.dao.objects.filter(
            community=community,
            is_cycle=False
        )

        # 状态过滤
        status_filter = filters.get('status')
        if status_filter is not None and status_filter != BusinessMeetingStatus.CANCELLED.value:
            # 用数据库 status 字段筛选
            query_set = query_set.filter(status=status_filter).filter(is_delete=0)
        elif status_filter == BusinessMeetingStatus.CANCELLED.value:
            # 已取消状态用 is_delete 筛选
            query_set = query_set.filter(is_delete=1)

        # 日期筛选
        date = filters.get('date')
        if date:
            query_set = query_set.filter(date=date)

        start_date = filters.get('start_date')
        end_date = filters.get('end_date')
        if start_date and end_date:
            query_set = query_set.filter(date__gte=start_date, date__lte=end_date)

        # 发起人筛选
        sponsor = filters.get('sponsor')
        if sponsor:
            sponsor = sponsor.split(",")
            query_set = query_set.filter(sponsor__in=sponsor)

        # SIG筛选
        group_name = filters.get('group_name')
        if group_name:
            query_set = query_set.filter(group_name__icontains=group_name)

        # 平台筛选
        platform = filters.get('platform')
        if platform:
            query_set = query_set.filter(platform=platform)

        # topic模糊查询
        topic = filters.get('topic')
        if topic:
            query_set = query_set.filter(topic__icontains=topic)

        # 私有会议过滤
        if not filters.get('include_private'):
            query_set = query_set.filter(is_private=False)

        # 添加sub_id=None标记，is_cycle字段已存在于模型中
        return query_set.annotate(
            sub_id=Value(None, output_field=CharField())
        ).values(
            'id', 'topic', 'sponsor', 'group_name', 'community', 'platform',
            'date', 'start', 'end', 'status', 'is_cycle', 'mid','is_delete',
            'agenda', 'etherpad', 'join_url', 'sub_id',
        )

    @classmethod
    def get_non_cycle_meetings_count(cls, community, filters):
        """获取非周期会议总数（用于分页计算）"""
        query_set = cls.dao.objects.filter(
            community=community,
            is_delete=0,
            is_cycle=False
        )

        # 日期筛选
        date = filters.get('date')
        if date:
            query_set = query_set.filter(date=date)

        start_date = filters.get('start_date')
        end_date = filters.get('end_date')
        if start_date and end_date:
            query_set = query_set.filter(date__gte=start_date, date__lte=end_date)

        # 发起人筛选
        sponsor = filters.get('sponsor')
        if sponsor:
            query_set = query_set.filter(sponsor=sponsor)

        # SIG筛选
        group_name = filters.get('group_name')
        if group_name:
            query_set = query_set.filter(group_name__icontains=group_name)

        # 平台筛选
        platform = filters.get('platform')
        if platform:
            query_set = query_set.filter(platform=platform)

        # topic模糊查询
        topic = filters.get('topic')
        if topic:
            query_set = query_set.filter(topic__icontains=topic)

        # 私有会议过滤
        if not filters.get('include_private'):
            query_set = query_set.filter(is_private=False)

        return query_set.count()
