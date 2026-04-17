#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
from dataclasses import dataclass

from meeting.infrastructure.adapter.meeting_adapter_impl.actions.base_action import CreateAction, \
    UpdateAction, DeleteAction, GetParticipantsAction, GetVideoAction, ForceEndAction, GetMeetingStatusAction


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

@dataclass
class ZoomGetMeetingStatusAction(GetMeetingStatusAction):
    mid: str