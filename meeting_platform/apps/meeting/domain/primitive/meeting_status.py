#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
from meeting_platform.utils.base_enum import EnumBase


class BusinessMeetingStatus(EnumBase):
    """会议状态"""
    NOT_STARTED = (0, '未开始')
    ONGOING = (1, '进行中')
    ENDED = (2, '已结束')
    OVERTIME = (3, '已超时')
    CANCELLED = (4, '已取消')