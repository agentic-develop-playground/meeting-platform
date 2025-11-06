#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @Time    : 2024/6/19 16:16
# @Author  : Tom_zc
# @FileName: tencent_action.py
# @Software: PyCharm
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