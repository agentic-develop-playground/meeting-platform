#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2025/3/30 11:25
# @Author  : Tom_zc
# @FileName: time_range.py
# @Software: PyCharm
import logging

from meeting_platform.utils.base_enum import EnumBase
from meeting_platform.utils.ret_api import MyValidationError
from meeting_platform.utils.ret_code import RetCode

logger = logging.getLogger("log")


class TimeRange(EnumBase):
    """查询的时间范围"""
    WEEKLY = (0, '前后一周的会议')
    RECENTLY = (1, '大于当前时间的会议')
    DAILY = (2, '今天的会议')
    AFTER_WEEKLY = (3, '今天之后一周内的会议')

    @classmethod
    def check_value(cls, value):
        value = int(value)
        if value not in [time_range.value for time_range in cls]:
            logger.error("receive the invalid value:{}".format(value))
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        return TimeRange(value)
