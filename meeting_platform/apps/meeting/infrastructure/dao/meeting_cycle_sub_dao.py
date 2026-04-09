#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.


from meeting.models import MeetingCycleSubMeeting
from django.db.models import Q
from meeting.domain.primitive.meeting_status import BusinessMeetingStatus


class MeetingCycleSubMeetingDao:
    _dao = MeetingCycleSubMeeting

    @classmethod
    def get_all(cls):
        return cls._dao.objects.all()

    @classmethod
    def get_by_mid(cls, mid):
        return cls._dao.objects.filter(mid=mid).all().values()

    @classmethod
    def get_by_mid_date(cls, mid, date):
        return cls._dao.objects.filter(mid=mid, date=date).first()

    @classmethod
    def get_by_date_range(cls, start_date, end_date, mid):
        return cls._dao.objects.filter(date__gte=start_date, date__lte=end_date, mid=mid).values_list("date", flat=True)

    @classmethod
    def get_first_by_date_range(cls, start_date, end_date, mid, sub_ids):
        return cls._dao.objects.filter(date__gte=start_date, date__lte=end_date, mid=mid, sub_id__in=sub_ids).first()

    @classmethod
    def get_counts_by_mid(cls, mid):
        return cls._dao.objects.filter(mid=mid).count()

    @classmethod
    def create(cls, **kwargs):
        return cls._dao.objects.create(**kwargs)

    @classmethod
    def get_by_mid_and_sub_id(cls, mid, sub_id):
        return cls._dao.objects.filter(mid=mid, sub_id=sub_id).first()

    @classmethod
    def get_by_sub_id(cls, sub_id):
        return cls._dao.objects.filter(sub_id=sub_id).first()

    @classmethod
    def delete_by_mid_and_sub_id(cls, mid, sub_id):
        return cls._dao.objects.filter(mid=mid, sub_id=sub_id).delete()

    @classmethod
    def delete_by_mid(cls, mid, cur_date_str, cur_time_str):
        return cls._dao.objects.filter(mid=mid).filter(Q(date__gt=cur_date_str) |
                                                       Q(date=cur_date_str, start__gt=cur_time_str)).delete()

    @classmethod
    def get_by_mid_and_date(cls, mid, cur_date_str, cur_time_str):
        return cls._dao.objects.filter(mid=mid).filter(Q(date__gt=cur_date_str) |
                                                       Q(date=cur_date_str, start__gt=cur_time_str)).all()

    @classmethod
    def update_by_mid_and_sub_id(cls, mid, sub_id, **kwargs):
        return cls._dao.objects.filter(mid=mid, sub_id=sub_id).update(**kwargs)

    @classmethod
    def get_status_sync_candidates(cls, community, today):
        """获取今天所有周期子会议

        新逻辑：查询今天的所有子会议，不再使用时间窗口过滤
        """
        return cls._dao.objects.filter(
            meeting__community=community,
            meeting__is_delete=0,
            date__gte=today
        ).select_related('meeting').all()

    @classmethod
    def get_ongoing_sub_meetings(cls, community):
        """获取正在进行中的周期子会议"""
        return cls._dao.objects.filter(
            meeting__community=community,
            meeting__is_delete=0,
            status=BusinessMeetingStatus.ONGOING.value
        ).select_related('meeting').all()

    @classmethod
    def update_status(cls, sub_meeting_id, status):
        """更新子会议状态"""
        from datetime import datetime
        return cls._dao.objects.filter(id=sub_meeting_id).update(
            status=status,
            status_updated_at=datetime.now()
        )

    @classmethod
    def clear_status(cls, sub_id):
        """清除子会议状态（会议结束时调用）"""
        from datetime import datetime
        return cls._dao.objects.filter(sub_id=sub_id).update(
            status=BusinessMeetingStatus.ENDED.value,
            status_updated_at=datetime.now(),
            warning_email_sent=False
        )

    @classmethod
    def get_upcoming_end_sub_meetings(cls, community, today, warning_minutes=10):
        """获取即将结束的周期子会议（用于发送预警邮件）

        条件：子会议.date=今天 AND end在当前时间到当前时间+warning_minutes之间 AND status in [1,3] AND warning_email_sent=False
        """
        from datetime import datetime, timedelta

        now = datetime.now()
        current_time = now.strftime('%H:%M')
        warning_time = (now + timedelta(minutes=warning_minutes)).strftime('%H:%M')

        return cls._dao.objects.filter(
            meeting__community=community,
            meeting__is_delete=0,
            date=today,
            end__gte=current_time,
            end__lte=warning_time,
            status__in=[BusinessMeetingStatus.ONGOING.value, BusinessMeetingStatus.OVERTIME.value],
            warning_email_sent=False
        ).select_related('meeting').all()

    @classmethod
    def get_ongoing_sub_meetings_for_warning(cls, community, today):
        """获取当天所有需要预警检查的周期子会议（进行中/超时且未发送预警）

        注意：不再限制结束时间窗口，由业务逻辑动态判断预警时机
        """
        from datetime import datetime

        now = datetime.now()
        current_time = now.strftime('%H:%M')

        return cls._dao.objects.filter(
            meeting__community=community,
            meeting__is_delete=0,
            date=today,
            end__gte=current_time,  # 结束时间 >= 当前时间（会议未结束）
            status__in=[BusinessMeetingStatus.ONGOING.value, BusinessMeetingStatus.OVERTIME.value],
            warning_email_sent=False
        ).select_related('meeting').all()

    @classmethod
    def get_next_sub_meeting_start_time(cls, community, host_id, today, current_end_time):
        """获取当天该host_id的下一场周期子会议的开始时间

        Args:
            community: 社区
            host_id: 会议主持人邮箱
            today: 今天日期
            current_end_time: 当前会议结束时间

        Returns:
            str: 下一场子会议的开始时间 (HH:MM)，如果没有后续子会议返回 None
        """
        next_meeting = cls._dao.objects.filter(
            meeting__community=community,
            meeting__host_id=host_id,
            meeting__is_delete=0,
            date=today,
            start__gt=current_end_time
        ).order_by('start').first()

        if next_meeting:
            return next_meeting.start
        return None

    @classmethod
    def mark_warning_email_sent(cls, sub_meeting_id):
        """标记已发送预警邮件"""
        return cls._dao.objects.filter(id=sub_meeting_id).update(warning_email_sent=True)

    @classmethod
    def has_subsequent_sub_meetings(cls, community, host_id, today, current_end_time):
        """检查当天该host_id是否有后续周期子会议

        Args:
            community: 社区
            host_id: 会议主持人邮箱
            today: 今天日期
            current_end_time: 当前会议结束时间

        Returns:
            bool: 是否有后续子会议
        """
        return cls._dao.objects.filter(
            meeting__community=community,
            meeting__host_id=host_id,
            meeting__is_delete=0,
            date=today,
            start__gt=current_end_time
        ).exists()

    @classmethod
    def reset_warning_email_status(cls, sub_id):
        """重置预警邮件状态（子会议开始时调用）"""
        return cls._dao.objects.filter(sub_id=sub_id).update(warning_email_sent=False)

    @classmethod
    def get_expanded_sub_meetings(cls, community, filters):
        """获取周期子会议列表（展开后用于合并会议列表接口）

        返回格式与非周期会议一致，便于合并排序
        """
        query_set = cls._dao.objects.filter(
            meeting__community=community,
            meeting__is_delete=0
        ).select_related('meeting')

        # 日期筛选
        date = filters.get('date')
        if date:
            query_set = query_set.filter(date=date)

        start_date = filters.get('start_date')
        end_date = filters.get('end_date')
        if start_date and end_date:
            query_set = query_set.filter(date__gte=start_date, date__lte=end_date)

        # 发起人筛选（通过父会议）
        sponsor = filters.get('sponsor')
        if sponsor:
            query_set = query_set.filter(meeting__sponsor=sponsor)

        # SIG筛选
        group_name = filters.get('group_name')
        if group_name:
            query_set = query_set.filter(meeting__group_name__icontains=group_name)

        # 平台筛选
        platform = filters.get('platform')
        if platform:
            query_set = query_set.filter(meeting__platform=platform)

        # 私有会议过滤
        if not filters.get('include_private'):
            query_set = query_set.filter(meeting__is_private=False)

        # 返回展开后的结果
        result = []
        for sub in query_set.all():
            result.append({
                'id': sub.meeting.id,
                'topic': sub.meeting.topic,
                'sponsor': sub.meeting.sponsor,
                'group_name': sub.meeting.group_name,
                'community': sub.meeting.community,
                'platform': sub.meeting.platform,
                'date': sub.date,
                'start': sub.start,
                'end': sub.end,
                'status': sub.status,
                'is_cycle': True,
                'sub_id': sub.sub_id,
                'mid': sub.mid,
                'is_delete': sub.meeting.is_delete
            })
        return result

    @classmethod
    def get_expanded_sub_meetings_queryset(cls, community, filters):
        """获取周期子会议QuerySet（用于UNION合并查询）

        返回ValuesQuerySet，字段顺序与非周期会议一致
        注意：Django union()按位置合并，所以字段顺序必须一致
        """
        query_set = cls._dao.objects.filter(
            meeting__community=community,
        ).select_related('meeting')

        # 状态过滤
        status_filter = filters.get('status')
        if status_filter is not None and status_filter != BusinessMeetingStatus.CANCELLED.value:
            # 用数据库 status 字段筛选
            query_set = query_set.filter(meeting__status=status_filter).filter(meeting__is_delete=0)
        elif status_filter == BusinessMeetingStatus.CANCELLED.value:
            # 已取消状态用 is_delete 筛选
            query_set = query_set.filter(meeting__is_delete=1)

        # 日期筛选
        date = filters.get('date')
        if date:
            query_set = query_set.filter(date=date)

        start_date = filters.get('start_date')
        end_date = filters.get('end_date')
        if start_date and end_date:
            query_set = query_set.filter(date__gte=start_date, date__lte=end_date)

        # 发起人筛选（通过父会议）
        sponsor = filters.get('sponsor')
        if sponsor:
            query_set = query_set.filter(meeting__sponsor=sponsor)

        # SIG筛选
        group_name = filters.get('group_name')
        if group_name:
            query_set = query_set.filter(meeting__group_name__icontains=group_name)

        # 平台筛选
        platform = filters.get('platform')
        if platform:
            query_set = query_set.filter(meeting__platform=platform)

        # topic模糊查询（通过父会议的topic）
        topic = filters.get('topic')
        if topic:
            query_set = query_set.filter(meeting__topic__icontains=topic)

        # 私有会议过滤
        if not filters.get('include_private'):
            query_set = query_set.filter(meeting__is_private=False)

        # 字段顺序必须与非周期会议完全一致
        # union()后的结果将使用第一个queryset的字段名
        return query_set.values(
            'meeting__id', 'meeting__topic', 'meeting__sponsor', 'meeting__group_name',
            'meeting__community', 'meeting__platform', 'date', 'start', 'end',
            'status', 'meeting__is_cycle', 'mid',  'meeting__is_delete',
            'meeting__agenda', 'meeting__etherpad', 'meeting__join_url', 'sub_id'
        )

    @classmethod
    def get_expanded_sub_meetings_count(cls, community, filters):
        """获取周期子会议总数（用于分页计算）"""
        query_set = cls._dao.objects.filter(
            meeting__community=community,
            meeting__is_delete=0
        )

        # 日期筛选
        date = filters.get('date')
        if date:
            query_set = query_set.filter(date=date)

        start_date = filters.get('start_date')
        end_date = filters.get('end_date')
        if start_date and end_date:
            query_set = query_set.filter(date__gte=start_date, date__lte=end_date)

        # 发起人筛选（通过父会议）
        sponsor = filters.get('sponsor')
        if sponsor:
            sponsor = sponsor.split(",")
            query_set = query_set.filter(sponsor__in=sponsor)

        # SIG筛选
        group_name = filters.get('group_name')
        if group_name:
            query_set = query_set.filter(meeting__group_name__icontains=group_name)

        # 平台筛选
        platform = filters.get('platform')
        if platform:
            query_set = query_set.filter(meeting__platform=platform)

        # topic模糊查询（通过父会议的topic）
        topic = filters.get('topic')
        if topic:
            query_set = query_set.filter(meeting__topic__icontains=topic)

        # 私有会议过滤
        if not filters.get('include_private'):
            query_set = query_set.filter(meeting__is_private=False)

        return query_set.count()
