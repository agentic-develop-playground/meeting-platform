import logging

from django.core.management.base import BaseCommand
from django.db import models

from meeting.models import User

logger = logging.getLogger('log')

class Group(models.Model):
    """用户组表"""
    name = models.CharField(verbose_name='组名', max_length=50)
    group_type = models.SmallIntegerField(verbose_name='组别', choices=((1, 'SIG'), (2, 'MSG'), (3, 'Pro')), null=True,
                                          blank=True)
    etherpad = models.CharField(verbose_name='etherpad', max_length=128, null=True, blank=True)
    create_time = models.DateTimeField(verbose_name='创建时间', auto_now_add=True, null=True, blank=True)

    class Meta:
        db_table = "meetings_group"
        verbose_name = "meetings_group"
        verbose_name_plural = verbose_name
        managed = False  # 不让 Django 管理迁移


class OldBaseMeeting(models.Model):
    topic = models.CharField(verbose_name='会议主题', max_length=128)
    community = models.CharField(verbose_name='社区', max_length=40, null=True, blank=True)
    group_name = models.CharField(verbose_name='SIG组', max_length=40, default='')
    sponsor = models.CharField(verbose_name='发起人', max_length=60)
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
        managed = False  # 不让 Django 管理迁移


class OldMeetingOld(OldBaseMeeting):
    """会议表"""
    group_type = models.SmallIntegerField(verbose_name='组别', choices=((1, 'SIG'), (2, 'MSG'), (3, 'Pro')))
    city = models.CharField(verbose_name='城市', max_length=10, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING)
    group = models.ForeignKey(Group, on_delete=models.DO_NOTHING)
    meeting_type = models.SmallIntegerField(verbose_name='会议类型', choices=((1, 'SIG'), (2, 'MSG'), (3, '专家委员会')),
                                            null=True, blank=True)
    replay_url = models.CharField(verbose_name='回放地址', max_length=255, null=True, blank=True)
    mplatform = models.CharField(verbose_name='第三方会议平台', max_length=20, null=True, blank=True, default='tencent')
    record = models.BooleanField(verbose_name="是否录制", null=True, blank=True)

    class Meta:
        db_table = "meetings_meeting"
        verbose_name = "meetings_meeting"
        verbose_name_plural = verbose_name
        managed = False  # 不让 Django 管理迁移

class OldRecord(models.Model):
    meeting_code = models.CharField(verbose_name='会议代码', max_length=20, null=True, blank=True)
    file_size = models.CharField(verbose_name='文件大小', max_length=20, null=True, blank=True)
    download_url = models.CharField(verbose_name='文件地址', max_length=255, null=True, blank=True)

    class Meta:
        db_table = "meetings_record"
        verbose_name = "meetings_record"
        verbose_name_plural = verbose_name
        managed = False  # 不让 Django 管理迁移

class Command(BaseCommand):
    OldMeeting = OldMeetingOld

    def _migrate_meetings(self):
        from meeting.models import Meeting

        field_map = {
            'topic': 'topic',
            'community': 'community',
            'group_name': 'group_name',
            'sponsor': 'sponsor',
            'date': 'date',
            'start': 'start',
            'end': 'end',
            'agenda': 'agenda',
            'etherpad': 'etherpad',
            'emaillist': 'email_list',
            'host_id': 'host_id',
            'mid': 'mid',
            'mmid': 'm_mid',
            'join_url': 'join_url',
            'create_time': 'create_time',
            'is_delete': 'is_delete',
            'mplatform': 'platform',
            'record': 'is_record',
        }

        old_meetings = OldMeetingOld.objects.using('mindspore_meetings_v2').all()
        res = []
        for old_meeting in old_meetings:
            logger.info(f'Importing meeting: {old_meeting}')
            new_meeting = {}
            for old_field, new_field in field_map.items():
                new_meeting[new_field] = getattr(old_meeting, old_field)
            new_meeting['sequence'] = 0  # Default value for new field
            new_meeting['update_time'] = None
            new_meeting['is_cycle'] = 0
            res.append(new_meeting)
            logger.info(f'Imported meeting data: {new_meeting}')
        Meeting.objects.bulk_create([Meeting(**data) for data in res])
        logger.info(f'Meeting import completed. There are {len(res)} records in total.')

    def _migrate_records(self):
        from meeting.models import Meeting, MeetingObsRecords
        from meeting.domain.primitive.upload_status import UploadStatus

        old_records = OldRecord.objects.using('mindspore_meetings_v2').all()
        res = []
        for old_record in old_records:
            logger.info(f'Importing record: {old_record}')
            # 通过meeting_code(mid)找到对应的Meeting
            try:
                meeting = Meeting.objects.get(mid=old_record.meeting_code)
            except Meeting.DoesNotExist:
                logger.warning(f'Meeting not found for mid: {old_record.meeting_code}, skipping record')
                continue

            # 创建MeetingObsRecords记录
            new_record = {
                'mid': old_record.meeting_code,
                'sub_id': None,  # 旧数据没有sub_id字段
                'status': UploadStatus.FINISH.value,  # 旧数据都是已完成的记录
                'text_vtt_url': None,
                'text_json_url': None,
                'text_video_url': old_record.download_url,  # download_url对应视频地址
                'text_picture_url': None,
                'topic_url': None,
                'meeting_id': meeting.id,
            }
            res.append(new_record)
            logger.info(f'Imported record data: {new_record}')

        MeetingObsRecords.objects.bulk_create([MeetingObsRecords(**data) for data in res])
        logger.info(f'Record import completed. There are {len(res)} records in total.')
        

    def handle(self, *args, **options):
        self._migrate_meetings()
        self._migrate_records()
    