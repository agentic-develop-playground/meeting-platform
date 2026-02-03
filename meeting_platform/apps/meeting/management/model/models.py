from meeting_platform.apps.meeting.management.model.base import BaseUser, BaseMeeting, BaseActivity, Video as commonVideo
from django.db import models


class User(BaseUser):
    """用户表"""

    USERNAME_FIELD = 'id'

    class Meta:
        db_table = "meetings_user"
        verbose_name = "meetings_user"
        verbose_name_plural = verbose_name
        managed = False  # 不让 Django 管理迁移


class Group(models.Model):
    """SIG组表"""
    group_name = models.CharField(verbose_name='组名', max_length=128, unique=True)
    maillist = models.EmailField(verbose_name='邮件列表', null=True, blank=True)
    etherpad = models.CharField(verbose_name='etherpad', max_length=255, null=True, blank=True)

    class Meta:
        db_table = "meetings_group"
        verbose_name = "meetings_group"
        verbose_name_plural = verbose_name
        managed = False  # 不让 Django 管理迁移


class GroupUser(models.Model):
    """组与用户表"""
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('group', 'user')
        db_table = "meetings_groupuser"
        verbose_name = "meetings_groupuser"
        verbose_name_plural = verbose_name
        managed = False  # 不让 Django 管理迁移


class OldMeeting(BaseMeeting):
    """会议表"""
    start_url = models.TextField(verbose_name='开启会议url', null=True, blank=True)
    timezone = models.CharField(verbose_name='时区', max_length=50, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    group = models.ForeignKey(Group, on_delete=models.DO_NOTHING)
    mplatform = models.CharField(verbose_name='第三方会议平台', max_length=20, null=True, blank=True, default='zoom')

    class Meta:
        db_table = "meetings_meeting"
        verbose_name = "meetings_meeting"
        verbose_name_plural = verbose_name
        managed = False  # 不让 Django 管理迁移


class Collect(models.Model):
    """用户收藏会议表"""
    meeting = models.ForeignKey(OldMeeting, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('meeting', 'user')
        db_table = "meetings_collect"
        verbose_name = "meetings_collect"
        verbose_name_plural = verbose_name
        managed = False  # 不让 Django 管理迁移


class Video(commonVideo):
    """会议记录表"""

    class Meta:
        db_table = "meetings_video"
        verbose_name = "meetings_video"
        verbose_name_plural = verbose_name
        managed = False  # 不让 Django 管理迁移


class OldRecord(models.Model):
    """录像表"""
    mid = models.CharField(verbose_name='会议id', max_length=12)
    platform = models.CharField(verbose_name='平台', max_length=50)
    url = models.CharField(verbose_name='播放地址', max_length=128, null=True, blank=True)
    thumbnail = models.CharField(verbose_name='缩略图', max_length=128, null=True, blank=True)

    class Meta:
        db_table = "meetings_record"
        verbose_name = "meetings_record"
        verbose_name_plural = verbose_name
        managed = False  # 不让 Django 管理迁移


class Activity(BaseActivity):
    """活动表"""
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    date = models.CharField(verbose_name='活动日期', max_length=30)
    live_address = models.CharField(verbose_name='直播地址', max_length=255, null=True, blank=True)
    start = models.CharField(verbose_name='开始时间', max_length=10, null=True, blank=True)
    end = models.CharField(verbose_name='结束时间', max_length=10, null=True, blank=True)
    start_url = models.TextField(verbose_name='主持人入口', null=True, blank=True)
    join_url = models.CharField(verbose_name='观众入口', max_length=255, null=True, blank=True)
    mid = models.CharField(verbose_name='网络研讨会id', max_length=20, null=True, blank=True)

    class Meta:
        db_table = "meetings_activity"
        verbose_name = "meetings_activity"
        verbose_name_plural = verbose_name
        managed = False  # 不让 Django 管理迁移


class ActivityCollect(models.Model):
    """用户收藏活动表"""
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('activity', 'user')
        db_table = "meetings_activitycollect"
        verbose_name = "meetings_activitycollect"
        verbose_name_plural = verbose_name
        managed = False  # 不让 Django 管理迁移
