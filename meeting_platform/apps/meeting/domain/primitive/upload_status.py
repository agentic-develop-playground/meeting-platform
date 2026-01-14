#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
from meeting_platform.utils.base_enum import EnumBase


class UploadStatus(EnumBase):
    """上传状态"""
    INIT = (0, '初始化')
    TRANSLATE = (1, '完成请求翻译')
    FINISH = (10, '已经上传完成')
