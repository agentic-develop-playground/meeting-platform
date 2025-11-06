#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2024/7/9 20:29
# @Author  : Tom_zc
# @FileName: zoom_action.py
# @Software: PyCharm
from dataclasses import dataclass

from meeting.infrastructure.adapter.meeting_adapter_impl.actions.base_action import CreateAction, \
    UpdateAction, DeleteAction, GetParticipantsAction, GetVideoAction, ForceEndAction


@dataclass
class ZoomCreateAction(CreateAction):
    date: str
    start: str
    end: str
    topic: str
    is_record: bool


@dataclass
class ZoomUpdateAction(UpdateAction):
    mid: str
    date: str
    start: str
    end: str
    topic: str
    is_record: bool


@dataclass
class ZoomDeleteAction(DeleteAction):
    mid: str


@dataclass
class ZoomGetParticipantsAction(GetParticipantsAction):
    mid: str


@dataclass
class ZoomGetVideo(GetVideoAction):
    mid: str

@dataclass
class ZoomForceEndAction(ForceEndAction):
    mid: str