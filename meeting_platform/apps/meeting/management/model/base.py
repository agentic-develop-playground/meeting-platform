# -*- coding: utf-8 -*-
# @Time    : 2023/10/13 11:52
# @Author  : Tom_zc
# @FileName: models.py
# @Software: PyCharm
import unicodedata
from django.db import models


# noinspection PyUnresolvedReferences
class MyAbstractBaseUser(models.Model):
    is_active = True

    REQUIRED_FIELDS = []

    class Meta:
        abstract = True

    def __str__(self):
        return self.get_username()

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def get_username(self):
        """Return the username for this User."""
        return getattr(self, self.USERNAME_FIELD)

    def clean(self):
        setattr(self, self.USERNAME_FIELD, self.normalize_username(self.get_username()))

    def natural_key(self):
        return (self.get_username(),)

    @property
    def is_anonymous(self):
        """
        Always return False. This is a way of comparing User objects to
        anonymous users.
        """
        return False

    @property
    def is_authenticated(self):
        """
        Always return True. This is a way to tell if the user has been
        authenticated in templates.
        """
        return True

    @classmethod
    def get_email_field_name(cls):
        try:
            return cls.EMAIL_FIELD
        except AttributeError:
            return 'email'

    @classmethod
    def normalize_username(cls, username):
        return unicodedata.normalize('NFKC', username) if isinstance(username, str) else username


class BaseUser(MyAbstractBaseUser):
    gitee_name = models.CharField(verbose_name='gitee名称', max_length=40, null=True, blank=True)
    nickname = models.CharField(verbose_name='昵称', max_length=40, null=True, blank=True)
    avatar = models.CharField(verbose_name='用户头像', max_length=255, null=True, blank=True)
    openid = models.CharField(verbose_name='openid', max_length=128, unique=True, null=True, blank=True)
    level = models.SmallIntegerField(verbose_name='会议权限', choices=((1, '普通用户'), (2, '授权用户'), (3, '管理员')),
                                     default=1)
    activity_level = models.SmallIntegerField(verbose_name='活动权限', choices=((1, '普通用户'), (2, '活动发起人'), (3, '管理员')),
                                              default=1)
    signature = models.CharField(verbose_name='签名', max_length=255, blank=True, null=True)
    refresh_signature = models.CharField(verbose_name='刷新签名', max_length=255, blank=True, null=True)
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True, null=True, blank=True)
    last_login = models.DateTimeField(verbose_name='上次登录时间', auto_now=True, null=True, blank=True)
    agree_privacy_policy = models.BooleanField(verbose_name='同意隐私政策', default=False)
    agree_privacy_policy_time = models.DateTimeField(verbose_name='同意隐私政策时间', null=True, blank=True)
    agree_privacy_policy_version = models.CharField(verbose_name='同意隐私政策版本', max_length=20, null=True, blank=True)
    agree_privacy_app_policy_version = models.CharField(verbose_name='同意隐私政策应用版本', max_length=20, null=True, blank=True)
    revoke_agreement_time = models.DateTimeField(verbose_name='撤销同意隐私声明时间', null=True, blank=True)
    is_delete = models.SmallIntegerField(verbose_name='是否删除', choices=((0, '否'), (1, '是')), default=0)
    logoff_time = models.DateTimeField(verbose_name='注销时间', null=True, blank=True)

    class Meta:
        abstract = True


class BaseMeeting(models.Model):
    topic = models.CharField(verbose_name='会议主题', max_length=128)
    community = models.CharField(verbose_name='社区', max_length=40, null=True, blank=True)
    group_name = models.CharField(verbose_name='SIG组', max_length=40, default='')
    sponsor = models.CharField(verbose_name='发起人', max_length=20)
    date = models.CharField(verbose_name='会议日期', max_length=30)
    start = models.CharField(verbose_name='会议开始时间', max_length=30)
    end = models.CharField(verbose_name='会议结束时间', max_length=30)
    duration = models.IntegerField(verbose_name='会议时长', null=True, blank=True)
    agenda = models.TextField(verbose_name='议程', default='', null=True, blank=True)
    etherpad = models.CharField(verbose_name='etherpad', max_length=255, null=True, blank=True)
    emaillist = models.TextField(verbose_name='邮件列表', null=True, blank=True)
    host_id = models.EmailField(verbose_name='host_id', null=True, blank=True)
    mid = models.CharField(verbose_name='会议id', max_length=20)
    mmid = models.CharField(verbose_name='腾讯会议id', max_length=20, null=True, blank=True)
    join_url = models.CharField(verbose_name='进入会议url', max_length=128, null=True, blank=True)
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True, null=True, blank=True)
    is_delete = models.SmallIntegerField(verbose_name='是否删除', choices=((0, '否'), (1, '是')), default=0)

    class Meta:
        abstract = True


class BaseActivity(models.Model):
    title = models.CharField(verbose_name='活动标题', max_length=50)
    activity_type = models.SmallIntegerField(verbose_name='活动类型', choices=((1, '线下'), (2, '线上'), (3, '线上与线下')))
    address = models.CharField(verbose_name='地理位置', max_length=100, null=True, blank=True)
    detail_address = models.CharField(verbose_name='详细地址', max_length=100, null=True, blank=True)
    longitude = models.DecimalField(verbose_name='经度', max_digits=8, decimal_places=5, null=True, blank=True)
    latitude = models.DecimalField(verbose_name='纬度', max_digits=8, decimal_places=5, null=True, blank=True)
    register_url = models.CharField(verbose_name='报名链接', max_length=255, null=True, blank=True)
    synopsis = models.TextField(verbose_name='活动简介', null=True, blank=True)
    schedules = models.TextField(verbose_name='日程', null=True, blank=True)
    poster = models.SmallIntegerField(verbose_name='海报', choices=((1, '主题1'), (2, '主题2'), (3, '主题3'), (4, '主题4')),
                                      default=1)
    status = models.SmallIntegerField(verbose_name='状态',
                                      choices=((1, '草稿'), (2, '审核中'), (3, '报名中'), (4, '进行中'), (5, '已结束')), default=1)
    wx_code = models.TextField(verbose_name='微信二维码', null=True, blank=True)
    is_delete = models.SmallIntegerField(verbose_name='是否删除', choices=((0, '未删除'), (1, '已删除')), default=0)
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True)
    sign_url = models.CharField(verbose_name='签到二维码', max_length=255, null=True, blank=True)
    replay_url = models.CharField(verbose_name='回放地址', max_length=255, null=True, blank=True)

    class Meta:
        abstract = True


class Video(models.Model):
    """会议记录表"""
    mid = models.CharField(verbose_name='会议id', max_length=12)
    topic = models.CharField(verbose_name='会议名称', max_length=50)
    community = models.CharField(verbose_name='社区', max_length=40, null=True, blank=True)
    group_name = models.CharField(verbose_name='所属sig组', max_length=50)
    agenda = models.TextField(verbose_name='会议简介', null=True, blank=True)
    attenders = models.TextField(verbose_name='参会人', null=True, blank=True)
    start = models.CharField(verbose_name='记录开始时间', max_length=30, null=True, blank=True)
    end = models.CharField(verbose_name='记录结束时间', max_length=30, null=True, blank=True)
    total_size = models.IntegerField(verbose_name='总文件大小', null=True, blank=True)
    download_url = models.CharField(verbose_name='下载地址', max_length=255, null=True, blank=True)
    replay_url = models.CharField(verbose_name='回放地址', max_length=255, null=True, blank=True)
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True, null=True, blank=True)
    text_vtt_url = models.CharField(verbose_name='文本vtt地址', max_length=255, null=True, blank=True)
    text_json_url = models.CharField(verbose_name='文本json地址', max_length=255, null=True, blank=True)
    text_video_url = models.CharField(verbose_name='文本video地址', max_length=255, null=True, blank=True)

    class Meta:
        abstract = True