#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
from enum import Enum


class EnumBase(Enum):
    """枚举基类"""

    def __new__(cls, *args):
        """将定义的属性拆分，不影响 value 的正常使用"""
        obj = object.__new__(cls)
        if len(args) > 1:
            obj._value_ = args[0]  # 实际值还是给 value 使用
            obj.des = args[1]
        else:
            obj._value_ = args[0]
        return obj

    @classmethod
    def to_tuple(cls):
        return tuple([(_.value, _.des) for _ in cls])
