#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2024/8/26 11:16
# @Author  : Tom_zc
# @FileName: handle_recordings.py
# @Software: PyCharm
import os
import shutil
import logging
import datetime
import traceback
from multiprocessing.dummy import Pool as ThreadPool

from django.conf import settings
from django.core.management.base import BaseCommand
from django.forms import model_to_dict

from meeting_platform.utils.common import execute_cmd3
from meeting_platform.utils.file_stream import write_content
from meeting.domain.primitive.upload_status import UploadStatus
from meeting.infrastructure.adapter.bilibili_adapter_impl import BiliAdapterImpl
from meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl import MeetingAdapterImpl
from meeting.infrastructure.adapter.upload_adapter_impl.bili_upload_adapter_impl import BiliUploadAdapterImpl
from meeting.infrastructure.adapter.upload_adapter_impl.obs_upload_adapter_impl import ObsUploadAdapterImpl
from meeting.infrastructure.dao.meeting_dao import MeetingDao

logger = logging.getLogger("log")


class HandleRecording:
    meeting_dao = MeetingDao
    meeting_adapter_impl = MeetingAdapterImpl()
    bili_adapter_impl = BiliAdapterImpl
    upload_obs_adapter_impl = ObsUploadAdapterImpl
    upload_bili_adapter_impl = BiliUploadAdapterImpl

    def __init__(self, community):
        self.community = community

    # noinspection LongLine
    def _cover_content(self, topic, group_name, date, start_time, end_time):
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
                <p style="font-size: 100px;margin-top: 150px; color: white"><b>{0}</b></p>
                <p style="font-size: 80px; margin: 0; color: white">SIG: {1}</p>
                <p style="font-size: 60px; margin: 0; color: white">Time: {2} {3}-{4}</p>
            </div>
        </body>
        </html>
        """.format(topic, group_name, date, start_time, end_time)
        return content

    def _get_video_path(self, meeting):
        """get video path in local file system"""
        video_path = self.meeting_adapter_impl.get_video(meeting)
        if not video_path:
            logger.error('[HandleRecording/_get_video_path]  {}/{}: video path could not be empty'.
                         format(self.community, meeting["mid"]))
            return
        if not os.path.exists(video_path):
            logger.error('[HandleRecording/_get_video_path]  {}/{}: video path could not be exist'.
                         format(self.community, meeting["mid"]))
            return
        if os.path.getsize(video_path) == 0:
            logger.error('[HandleRecording/_get_video_path] {}/{}: download but size is 0'.
                         format(self.community, meeting["mid"]))
            return
        return video_path

    def _get_video_cover_path(self, video_path, meeting):
        """get cover image"""
        # parse parameter
        html_path = video_path.replace('.mp4', '.html')
        image_path = video_path.replace('.mp4', '.png')
        mid = meeting["mid"]
        topic = meeting["topic"]
        group_name = meeting["group_name"]
        date = meeting["date"]
        start = meeting["start"]
        end = meeting["end"]
        community = meeting["community"]
        content = self._cover_content(topic, group_name, date, start, end)
        # write content to html
        write_content(html_path, content, model="w")
        if not os.path.exists(os.path.join(os.path.dirname(video_path), 'cover.png')):
            shutil.copy("meeting_platform/templates/image/{}/cover.png".format(community), os.path.dirname(video_path))
        execute_cmd3("wkhtmltoimage --enable-local-file-access {} {}".format(html_path, image_path))
        logger.info("[HandleRecording/_generate_cover] {}/{}: generate cover success".format(self.community, mid))
        if not os.path.exists(image_path):
            logger.error('[HandleRecording/_get_video_cover_path] {}/{}: fail to generate cover for meeting video'
                         .format(self.community, meeting["mid"]))
            return
        return image_path

    def refresh_upload_status(self):
        """refresh_upload_status: if bili passed the video, and set the upload_status=UploadStatus.UPLOAD_ALL"""
        logger.info('[HandleRecording/check_upload_results] {}:Start to check results for uploaded videos to bili'.
                    format(self.community))
        adapter_impl = self.bili_adapter_impl(self.community)
        all_vid = adapter_impl.search_all_videos()
        uploaded_bili_mid = self.meeting_dao.get_uploaded_mid_by_community_and_status(self.community,
                                                                                      UploadStatus.UPLOAD_BILI.value)
        exist_mid = list(set(uploaded_bili_mid) - set(all_vid))
        logger.info('[HandleRecording/check_upload_results] {}:Find uploaded bili video:{}'.
                    format(self.community, ",".join(exist_mid)))
        self.meeting_dao.update_upload_status_by_community_and_mid(self.community, exist_mid,
                                                                   UploadStatus.UPLOAD_ALL.value)

    def _get_valid_query_range(self):
        cur_date = datetime.datetime.now()
        start_date = str(cur_date - datetime.timedelta(days=settings.BILI_UPLOAD_DATE))
        end_date = cur_date.strftime('%Y-%m-%d')
        return start_date, end_date

    def upload_all(self):
        """upload all: get video --> upload obs ---> upload bili"""
        start_date, end_date = self._get_valid_query_range()
        meeting_infos = self.meeting_dao.get_upload_all_by_community_and_status(self.community, UploadStatus.INIT.value,
                                                                                start_date, end_date)
        upload_mid = ",".join([str(i.mid) for i in meeting_infos])
        logger.info("[HandleRecording/upload_all]: Find need to upload mid({}/{})".format(upload_mid, self.community))
        for meeting in meeting_infos:
            try:
                meeting = model_to_dict(meeting)
                video_path = self._get_video_path(meeting)
                if not video_path:
                    logger.info("[HandleRecording/upload_all]: Find empty video_path({})".format(meeting["mid"]))
                    continue
                cover_path = self._get_video_cover_path(video_path, meeting)
                if not cover_path:
                    logger.info("[HandleRecording/upload_all]: Find empty cover_path({})".format(meeting["mid"]))
                    continue
                ret = self.upload_obs_adapter_impl(meeting).upload(video_path, cover_path)
                if not ret:
                    raise Exception("upload obs failed")
                self.meeting_dao.update_by_id(meeting["id"], upload_status=UploadStatus.UPLOAD_OBS.value)
                replay_url = self.upload_bili_adapter_impl(meeting).upload(video_path, cover_path)
                if not replay_url:
                    raise Exception("upload bili failed")
                self.meeting_dao.update_by_id(meeting["id"], upload_status=UploadStatus.UPLOAD_BILI.value,
                                              replay_url=replay_url)
                logger.info("[HandleRecording/upload_all]: handler success({})".format(meeting["mid"]))
            except Exception as e:
                logger.error("[HandleRecording/upload] e:{}, traceback:{}".format(str(e), traceback.format_exc()))

    def upload_bili(self):
        """upload bili: get video --> upload bili, this is pointer to upload bili failed"""
        start_date, end_date = self._get_valid_query_range()
        meeting_infos = self.meeting_dao.get_upload_all_by_community_and_status(self.community,
                                                                                UploadStatus.UPLOAD_OBS.value,
                                                                                start_date, end_date)
        upload_mid = ",".join([str(i.mid) for i in meeting_infos])
        logger.info("[HandleRecording/upload_bili] {}: Find need to upload mid({})".format(upload_mid, self.community))
        for meeting in meeting_infos:
            try:
                meeting = model_to_dict(meeting)
                video_path = self._get_video_path(meeting)
                if not video_path:
                    logger.info("[HandleRecording/upload_bili]: Find empty video_path({})".format(meeting["mid"]))
                    continue
                cover_path = self._get_video_cover_path(video_path, meeting)
                if not cover_path:
                    logger.info("[HandleRecording/upload_bili]: Find empty cover_path({})".format(meeting["mid"]))
                    continue
                replay_url = self.upload_bili_adapter_impl(meeting).upload(video_path, cover_path)
                if not replay_url:
                    raise Exception("upload bili failed")
                logger.error("the replay_url is:{}".format(replay_url))
                self.meeting_dao.update_by_id(meeting["id"], upload_status=UploadStatus.UPLOAD_BILI.value,
                                              replay_url=replay_url)
            except Exception as e:
                logger.error("[HandleRecording/upload_bili] e:{}, traceback:{}".format(str(e), traceback.format_exc()))


def work_flow(handle_recording: HandleRecording):
    """按照社区进行分类操作
        1.先将之前上传B站的数据状态更新
        2.下载本地再上传到OBS, 再上传bilibili
    :param handle_recording:
    :return:
    """
    try:
        handle_recording.refresh_upload_status()
        handle_recording.upload_all()
        handle_recording.upload_bili()
    except Exception as e:
        logger.error("[work_flow] e:{}, traceback:{}".format(e, traceback.format_exc()))


class Command(BaseCommand):
    def handle(self, *args, **options):
        logger.info('-' * 20 + ' start to handler recordings' + '-' * 20)
        logger.info('[handle] find community: {}'.format(",".join(settings.COMMUNITY_SUPPORT)))
        try:
            handler_recording_communities = [HandleRecording(i) for i in settings.COMMUNITY_SUPPORT]
            pool = ThreadPool()
            pool.map(work_flow, handler_recording_communities)
            pool.close()
            pool.join()
            logger.info('-' * 20 + 'All done' + '-' * 20)
        except Exception as e:
            logger.error("[handle_recordings/handle] err:{}, traceback:{}".format(str(e), traceback.format_exc()))