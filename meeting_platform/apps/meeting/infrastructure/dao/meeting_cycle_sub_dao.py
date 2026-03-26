#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.


from meeting.models import MeetingCycleSubMeeting
from django.db.models import Q


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
    def get_overtime_sub_meetings(cls, community, today):
        """获取超时的周期子会议

        条件：子会议.date=今天 AND 子会议.end < 当前时间 AND 子会议.is_ongoing=True
        """
        from datetime import datetime
        from meeting.models import Meeting

        now = datetime.now()
        current_time = now.strftime('%H:%M')

        return cls._dao.objects.filter(
            meeting__community=community,
            meeting__is_delete=0,
            date=today,
            end__lt=current_time,
            is_ongoing=True
        ).select_related('meeting').all()

    @classmethod
    def update_status(cls, sub_meeting_id, is_ongoing):
        """更新子会议状态"""
        from datetime import datetime
        return cls._dao.objects.filter(id=sub_meeting_id).update(
            is_ongoing=is_ongoing,
            ongoing_updated_at=datetime.now()
        )

    @classmethod
    def update_overtime_status(cls, sub_meeting_id, is_overtime):
        """更新子会议超时状态"""
        from datetime import datetime
        if is_overtime:
            return cls._dao.objects.filter(id=sub_meeting_id).update(
                is_overtime=is_overtime,
                overtime_detected_at=datetime.now()
            )
        else:
            return cls._dao.objects.filter(id=sub_meeting_id).update(
                is_overtime=is_overtime,
                overtime_detected_at=None
            )

    @classmethod
    def get_upcoming_end_sub_meetings(cls, community, today, warning_minutes=5):
        """获取即将结束的周期子会议（用于发送预警邮件）

        条件：子会议.date=今天 AND end在当前时间到当前时间+warning_minutes之间 AND is_ongoing=True AND warning_email_sent=False
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
            is_ongoing=True,
            warning_email_sent=False
        ).select_related('meeting').all()

    @classmethod
    def mark_warning_email_sent(cls, sub_meeting_id):
        """标记已发送预警邮件"""
        return cls._dao.objects.filter(id=sub_meeting_id).update(warning_email_sent=True)

    @classmethod
    def reset_warning_email_status(cls, sub_id):
        """重置预警邮件状态（子会议开始时调用）"""
        return cls._dao.objects.filter(sub_id=sub_id).update(warning_email_sent=False)

    @classmethod
    def clear_overtime_status(cls, sub_id):
        """清除子会议超时状态（会议正常结束或强制结束时调用）"""
        from datetime import datetime
        return cls._dao.objects.filter(sub_id=sub_id).update(
            is_overtime=False,
            overtime_detected_at=None,
            is_ongoing=False,
            ongoing_updated_at=datetime.now(),
            warning_email_sent=False
        )
