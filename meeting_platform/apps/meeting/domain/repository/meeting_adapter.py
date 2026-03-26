#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.

from abc import ABC, abstractmethod


class MeetingAdapter(ABC):
    meeting_type = None

    @abstractmethod
    def create(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def update(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def delete(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def get_participants(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def get_video(self, *args, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def force_end_meeting(self, *args, **kwargs):
        pass

    @abstractmethod
    def get_meeting_status(self, *args, **kwargs):
        """查询会议实时状态，返回 True/False"""
        raise NotImplementedError
