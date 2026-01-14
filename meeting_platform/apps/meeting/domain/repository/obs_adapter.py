#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.

from abc import ABC, abstractmethod


class ObsAdapter(ABC):
    @abstractmethod
    def get_object(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def get_object_metadata(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def list_objects(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def upload_file(self, *args, **kwargs):
        raise NotImplementedError
