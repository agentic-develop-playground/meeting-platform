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
        return cls.dao.objects.filter(community=community, is_delete=0, is_private=False).order_by("group_name").values_list("group_name", flat=True).distinct()

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
            filter(Q(date__gt=start_date) & Q(date__lte=end_date)).all()

    @classmethod
    def get_ongoing_candidates(cls, community, now):
        """获取需要同步状态的会议

        条件：预定开始时间-10分钟 <= 现在 <= 预定结束时间+2小时，或当前状态为进行中
        """
        from datetime import datetime, timedelta

        # 计算时间窗口
        start_window = (now - timedelta(minutes=10)).strftime('%H:%M')
        end_window = (now + timedelta(hours=2)).strftime('%H:%M')
        today = now.strftime('%Y-%m-%d')

        query_set = cls.dao.objects.filter(community=community, is_delete=0)

        # 非周期会议：时间窗口内或正在进行中
        non_cycle_meetings = query_set.filter(
            is_cycle=False,
            date=today,
            start__lte=end_window,
            end__gte=start_window
        ).all()

        # 正在进行中的会议（持续监控直到结束）
        ongoing_meetings = query_set.filter(is_cycle=False, is_ongoing=True).all()

        # 合并结果，去重
        meeting_ids = set()
        result = []
        for m in non_cycle_meetings:
            if m.id not in meeting_ids:
                meeting_ids.add(m.id)
                result.append(m)
        for m in ongoing_meetings:
            if m.id not in meeting_ids:
                meeting_ids.add(m.id)
                result.append(m)

        # 周期会议：查询今天有子会议在时间窗口内的
        cycle_meetings = query_set.filter(
            is_cycle=True,
            cycle_sub_meeting__date=today,
            cycle_sub_meeting__start__lte=end_window,
            cycle_sub_meeting__end__gte=start_window
        ).distinct().all()

        for m in cycle_meetings:
            if m.id not in meeting_ids:
                meeting_ids.add(m.id)
                result.append(m)

        # 正在进行中的周期会议
        ongoing_cycle_meetings = query_set.filter(
            is_cycle=True,
            cycle_sub_meeting__is_ongoing=True
        ).distinct().all()

        for m in ongoing_cycle_meetings:
            if m.id not in meeting_ids:
                meeting_ids.add(m.id)
                result.append(m)

        return result

    @classmethod
    def update_status(cls, meeting_id, is_ongoing):
        """更新会议状态"""
        from datetime import datetime
        return cls.dao.objects.filter(id=meeting_id).update(
            is_ongoing=is_ongoing,
            ongoing_updated_at=datetime.now()
        )

    @classmethod
    def get_overtime_meetings(cls, community, today):
        """获取超时的非周期会议

        条件：date=今天 AND end < 当前时间 AND is_ongoing=True
        """
        from datetime import datetime
        now = datetime.now()
        current_time = now.strftime('%H:%M')

        return cls.dao.objects.filter(
            community=community,
            is_delete=0,
            is_cycle=False,
            date=today,
            end__lt=current_time,
            is_ongoing=True
        ).all()

    @classmethod
    def update_overtime_status(cls, meeting_id, is_overtime):
        """更新会议超时状态"""
        from datetime import datetime
        if is_overtime:
            return cls.dao.objects.filter(id=meeting_id).update(
                is_overtime=is_overtime,
                overtime_detected_at=datetime.now()
            )
        else:
            return cls.dao.objects.filter(id=meeting_id).update(
                is_overtime=is_overtime,
                overtime_detected_at=None
            )

    @classmethod
    def get_upcoming_end_meetings(cls, community, today, warning_minutes=5):
        """获取即将结束的会议（用于发送预警邮件）

        条件：date=今天 AND end在当前时间到当前时间+warning_minutes之间 AND is_ongoing=True AND warning_email_sent=False
        """
        from datetime import datetime, timedelta

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
            is_ongoing=True,
            warning_email_sent=False
        ).all()

    @classmethod
    def mark_warning_email_sent(cls, meeting_id):
        """标记已发送预警邮件"""
        return cls.dao.objects.filter(id=meeting_id).update(warning_email_sent=True)

    @classmethod
    def reset_warning_email_status(cls, meeting_id):
        """重置预警邮件状态（会议开始时调用）"""
        return cls.dao.objects.filter(id=meeting_id).update(warning_email_sent=False)

    @classmethod
    def clear_overtime_status(cls, meeting_id):
        """清除超时状态（会议正常结束或强制结束时调用）"""
        from datetime import datetime
        return cls.dao.objects.filter(id=meeting_id).update(
            is_overtime=False,
            overtime_detected_at=None,
            is_ongoing=False,
            ongoing_updated_at=datetime.now(),
            warning_email_sent=False
        )
