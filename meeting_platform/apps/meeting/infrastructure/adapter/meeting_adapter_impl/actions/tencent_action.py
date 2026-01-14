#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
from dataclasses import dataclass

from meeting.infrastructure.adapter.meeting_adapter_impl.actions.base_action import CreateAction, \
    UpdateAction, DeleteAction, GetParticipantsAction, GetVideoAction, ForceEndAction


@dataclass
class TencentCreateAction(CreateAction):
    date: str
    start: str
    end: str
    topic: str
    is_record: bool


@dataclass
class TencentUpdateAction(UpdateAction):
    mid: str
    m_mid: str
    date: str
    start: str
    end: str
    topic: str
    is_record: bool


@dataclass
class TencentDeleteAction(DeleteAction):
    mid: str
    m_mid: str


@dataclass
class TencentGetParticipantsAction(GetParticipantsAction):
    m_mid: str


@dataclass
class TencentGetVideo(GetVideoAction):
    mid: str
    m_mid: str
    date: str
    start: str

@dataclass
class TencentForceEndAction(ForceEndAction):
    m_mid: str