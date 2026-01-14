#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.

from abc import ABC, abstractmethod


class MessageAdapter(ABC):
    @abstractmethod
    def send_message(self, *args, **kwargs):
        raise NotImplementedError
