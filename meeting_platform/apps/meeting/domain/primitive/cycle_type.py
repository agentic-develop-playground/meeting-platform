#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.


import logging

from meeting_platform.utils.base_enum import EnumBase
from meeting_platform.utils.ret_api import MyValidationError
from meeting_platform.utils.ret_code import RetCode

logger = logging.getLogger("log")


class CycleType(EnumBase):
    DAY = (0, 'Day')
    Week = (1, 'Week')
    Month = (2, 'Month')

    @classmethod
    def check_value(cls, value):
        value = int(value)
        if value not in [cycle_type.value for cycle_type in cls]:
            logger.error("receive the invalid value:{}".format(value))
            raise MyValidationError(RetCode.STATUS_PARAMETER_ERROR)
        return CycleType(value)
