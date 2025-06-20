#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2024/7/11 12:18
# @Author  : Tom_zc
# @FileName: bilibili_client.py
# @Software: PyCharm
from django.conf import settings

from meeting.domain.repository.bilibili_adapter import BiliAdapter
from meeting_platform.utils.client.bili_client import BiliClient


class BiliAdapterImpl(BiliClient, BiliAdapter):
    def __init__(self, community):
        """init bilibili adapter impl"""
        bili_info = settings.COMMUNITY_BILI[community]
        super(BiliAdapterImpl, self).__init__(bili_info["BILI_UID"], bili_info["BILI_JCT"],
                                              bili_info["BILI_SESS_DATA"], bili_info.get("SERIES_ID"))
