#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2024/8/26 16:21
# @Author  : Tom_zc
# @FileName: bili_client.py
# @Software: PyCharm
from django.conf import settings

from bilibili_api import video_uploader, sync, Credential
from bilibili_api.user import User


class BiliClient(object):
    def __init__(self, bili_uid, bili_jct, bili_sess_data):
        """init bilibili credential"""
        self.credential = Credential(bili_jct=bili_jct, sessdata=bili_sess_data)
        self.bili_uid = bili_uid
        self.bili_api_prefix = settings.API_PREFIX["BILIBILI_API_PREFIX"]

    def upload(self, meeting_info, video_path, thumbnail_path):
        tag = meeting_info.get('tag')
        title = meeting_info.get('title')
        desc = meeting_info.get('desc')
        page = video_uploader.VideoUploaderPage(path=video_path, title=title, description=desc)
        meta = {
            'copyright': 1,
            'desc': desc,
            'desc_format_id': 0,
            'dynamic': '',
            'interactive': 0,
            'no_reprint': 1,
            'subtitles': {
                'lan': '',
                'open': 0
            },
            'tag': tag,
            'tid': 124,
            'title': title
        }
        uploader = video_uploader.VideoUploader([page], meta, self.credential, cover=thumbnail_path)
        res = sync(uploader.start())
        return res

    def search_all_videos(self):
        user = User(self.bili_uid, self.credential)
        all_vid = []
        pn = 1
        while True:
            res = sync(user.get_videos(pn=pn))
            if len(res.get('list').get('vlist')) == 0:
                break
            for video in res['list']['vlist']:
                b_vid = video.get('bvid')
                if not b_vid:
                    continue
                if b_vid not in all_vid:
                    all_vid.append(b_vid)
            pn += 1
        return all_vid

    def get_replay_url(self, b_vid):
        return self.bili_api_prefix + b_vid
