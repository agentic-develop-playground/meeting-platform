#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
"""
1.扫描第三方会议的视频
2.上传到B站
"""

import os
import logging
import shutil
import traceback
from datetime import datetime
from email.header import Header
from email.mime.text import MIMEText
from multiprocessing.dummy import Pool as ThreadPool

from django.conf import settings
from django.core.management.base import BaseCommand

from meeting.infrastructure.adapter.bilibili_adapter_impl import BiliAdapterImpl
from meeting.infrastructure.adapter.meeting_adapter_impl.apis.zoom_api import ZoomApi
from meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl import MeetingAdapterImpl
from meeting.infrastructure.adapter.message_adapter_impl.email_adapter_impl import EmailAdapter
from meeting.infrastructure.adapter.upload_adapter_impl.bili_upload_adapter_impl import BiliUploadAdapterImpl
from meeting.infrastructure.adapter.upload_adapter_impl.obs_upload_adapter_impl import ObsUploadAdapterImpl
from meeting.infrastructure.dao.meeting_cache_dao import MeetingCacheDao
from meeting_platform.utils.common import execute_cmd3
from meeting_platform.utils.file_stream import write_content
from meeting_platform.utils.customized.my_trimmer import trimmer_video

logger = logging.getLogger("log")

_QUERY_DAY = 30


class ScanUploadRecording:
    meeting_adapter_impl = MeetingAdapterImpl()
    bili_adapter_impl = BiliAdapterImpl
    upload_obs_adapter_impl = ObsUploadAdapterImpl
    upload_bili_adapter_impl = BiliUploadAdapterImpl
    meeting_cache_dao = MeetingCacheDao()

    def __init__(self, community):
        self.community = community

    # noinspection LongLine
    @staticmethod
    def _cover_content(topic, date):
        """get the cover html template"""
        content = """
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <title>cover</title>
        </head>
        <body>
            <div style="display: inline-block; height: 688px; width: 1024px; text-align: center; background-image: url('cover.png')">
                <p style="font-size: 80px;margin-top: 200px; color: white"><b>{0}</b></p>
                <p style="font-size: 40px; margin: 0; color: white">Time: {1}</p>
            </div>
        </body>
        </html>
        """.format(topic, date)
        return content

    def _get_video_cover_path(self, video_path, meeting):
        """get cover image"""
        # parse parameter
        html_path = video_path.replace('.mp4', '.html')
        image_path = video_path.replace('.mp4', '.png')
        mid = meeting["mid"]
        topic = meeting["topic"]
        date = meeting["date"]
        community = meeting["community"]
        logger.info("[ScanUploadRecording/_generate_cover] {}/{}: start to generate cover".format(self.community, mid))
        content = self._cover_content(topic, date)
        # write content to html
        write_content(html_path, content, model="w")
        if not os.path.exists(os.path.join(os.path.dirname(video_path), 'cover.png')):
            shutil.copy("meeting_platform/templates/image/{}/cover.png".format(community), os.path.dirname(video_path))
        execute_cmd3("wkhtmltoimage --enable-local-file-access {} {}".format(html_path, image_path))
        if not os.path.exists(image_path):
            logger.error('[ScanUploadRecording/_get_video_cover_path] {}/{}: fail to generate cover for meeting video'
                         .format(self.community, meeting["mid"]))
            return
        return image_path

    def scan_video(self):
        host_ids = settings.COMMUNITY_HOST[self.community][ZoomApi.meeting_type.upper()]
        zoom_api = ZoomApi(self.community, ZoomApi.meeting_type.upper(), host_ids[0]["HOST"])
        video_infos = zoom_api.get_video_by_day(_QUERY_DAY)
        new_list = list()
        for video_info in video_infos:
            if not self.meeting_cache_dao.get_by_meeting_id(video_info["uuid"]):
                logger.info("find the need upload the meeting:{}".format(video_info["uuid"]))
                new_list.append(video_info)
        logger.info("find the new list:{}".format(len(new_list)))
        return zoom_api.get_video_url_by_records(records=new_list)

    def upload_bili(self, path_dict):
        for path, meeting_data in path_dict.items():
            meeting_date = datetime.strptime(meeting_data["start_time"], "%Y-%m-%dT%H:%M:%SZ")
            meeting = {
                "mid": meeting_data["id"],
                "community": self.community,
                "topic": meeting_data["topic"],
                "date": meeting_date.strftime("%Y-%m-%d"),
                "group_name": "VLLM"
            }
            cover_path = self._get_video_cover_path(path, meeting)
            path = trimmer_video(path, meeting_data["id"])
            impl = self.upload_bili_adapter_impl(meeting)
            vid = impl.upload(path, cover_path, return_replay_url=False)
            self.meeting_cache_dao.create(meeting_id=meeting_data["uuid"], vid=vid)


def send_failed_email(community, str_msg):
    email_config = settings.COMMUNITY_SMTP.get(community)
    adapter = EmailAdapter(community)
    msg = MIMEText("[scan_upload_meetings] error:{}".format(str_msg), "plain", "utf-8")
    msg['Subject'] = Header("vllm ascend error", 'utf-8')
    msg['To'] = email_config["SMTP_MESSAGE_TO"]
    adapter.send_message(receive_str=email_config["SMTP_MESSAGE_TO"], msg=msg)


def work_flow(handle_recording: ScanUploadRecording):
    """按照社区进行分类操作
        1.先从第三方视频下载
        2.上传bilibili
    :param handle_recording:
    :return:
    """
    try:
        path_dict = handle_recording.scan_video()
        if not path_dict:
            logger.info("get empty path_lists")
            return
        handle_recording.upload_bili(path_dict)
    except Exception as e:
        logger.error("[work_flow] e:{}, traceback:{}".format(e, traceback.format_exc()))
        send_failed_email(handle_recording.community, str(e))


class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info('-' * 20 + ' start to handler scan and upload meetings' + '-' * 20)
        logger.info('[handle] find community: {}'.format(",".join(settings.COMMUNITY_SUPPORT)))
        try:
            handler_recording_communities = [ScanUploadRecording(i) for i in settings.COMMUNITY_SUPPORT]
            pool = ThreadPool()
            pool.map(work_flow, handler_recording_communities)
            pool.close()
            pool.join()
            logger.info('-' * 20 + 'All done' + '-' * 20)
        except Exception as e:
            logger.error("[scan_upload_meetings/handle] err:{}, traceback:{}".format(str(e), traceback.format_exc()))
