#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
from dataclasses import dataclass

from meeting.infrastructure.adapter.meeting_adapter_impl.actions.base_action import CreateAction, \
    UpdateAction, DeleteAction, DeleteCycleAction, DeleteCycleSubAction, GetParticipantsAction, \
    GetVideoAction, CreateCycleAction, UpdateCycleAction, UpdateCycleSubAction, ForceEndAction


@dataclass
class WkCreateAction(CreateAction):
    date: str
    start: str
    end: str
    topic: str
    is_record: bool


@dataclass
class WkCreateCycleAction(CreateCycleAction):
    start_date: str
    end_date: str
    start: str
    end: str
    cycle_type: str
    interval: int
    point: [int]
    topic: str
    is_record: bool


@dataclass
class WkUpdateAction(UpdateAction):
    mid: str
    date: str
    start: str
    end: str
    topic: str
    is_record: bool


@dataclass
class WkUpdateCycleAction(UpdateCycleAction):
    mid: str
    start_date: str
    end_date: str
    start: str
    end: str
    cycle_type: str
    interval: int
    point: [int]
    topic: str
    is_record: bool


@dataclass
class WkUpdateCycleSubAction(UpdateCycleSubAction):
    mid: str
    sub_id: str
    date: str
    start: str
    end: str


@dataclass
class WkDeleteAction(DeleteAction):
    mid: str


@dataclass
class WkDeleteCycleAction(DeleteCycleAction):
    mid: str


@dataclass
class WkDeleteCycleSubAction(DeleteCycleSubAction):
    mid: str
    sub_id: str


@dataclass
class WkGetParticipantsAction(GetParticipantsAction):
    mid: str
    date: str
    start: str
    end: str


@dataclass
class WkGetVideo(GetVideoAction):
    mid: str
    date: str
    start: str
    end: str

@dataclass
class WkForceEndAction(ForceEndAction):
    mid: str