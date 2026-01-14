#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.

from abc import ABC, abstractmethod


class BiliAdapter(ABC):
    @abstractmethod
    def upload(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def search_all_videos(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def get_replay_url(self, *args, **kwargs):
        raise NotImplementedError
