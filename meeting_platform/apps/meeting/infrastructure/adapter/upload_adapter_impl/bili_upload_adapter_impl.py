#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
import logging
from meeting.domain.repository.upload_adapter import UploadAdapter
from meeting.infrastructure.adapter.bilibili_adapter_impl import BiliAdapterImpl
from meeting_platform.utils.common import func_retry

logger = logging.getLogger("log")


class BiliUploadAdapterImpl(UploadAdapter):

    def __init__(self, meeting):
        super(BiliUploadAdapterImpl, self).__init__(meeting)
        self.bili_adapter_impl = BiliAdapterImpl(meeting["community"])

    @func_retry()
    def upload(self, video_path, cover_path, return_replay_url=True):
        logger.info("start to upload the bili...")
        meeting_info = {
            'tag': '{}, SIG meeting, recording'.format(self.meeting["community"]),
            'title': '{}（{}）'.format(self.meeting["topic"], self.meeting["date"]),
            'desc': 'community meeting recording for {}'.format(self.meeting["group_name"])
        }
        res = self.bili_adapter_impl.upload(meeting_info, video_path, cover_path)
        if not isinstance(res, dict) or 'bvid' not in res.keys():
            logger.error('[BiliUploadAdapterImpl/upload] Unexpected upload result to bili: {}'.format(res))
            return None
        b_vid = str(res.get('bvid'))
        logger.info('[BiliUploadAdapterImpl/upload]meeting {}: upload to bili successfully, b_vid is {}'.
                    format(self.meeting["mid"], b_vid))
        if return_replay_url:
            return self.bili_adapter_impl.get_replay_url(b_vid)
        return b_vid

    @func_retry()
    def add_video(self, vid):
        return self.bili_adapter_impl.add_video(vid)
