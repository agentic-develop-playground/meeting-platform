#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.

from abc import ABC, abstractmethod


class UploadAdapter(ABC):
    def __init__(self, meeting):
        self.meeting = meeting

    @abstractmethod
    def upload(self, *args, **kwargs):
        raise NotImplementedError
