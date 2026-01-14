#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.


class BaseAction:
    function_action = None
    community = None


class CreateAction(BaseAction):
    function_action = "create"


class CreateCycleAction(BaseAction):
    function_action = "create_cycle"


class UpdateAction(BaseAction):
    function_action = "update"


class UpdateCycleAction(BaseAction):
    function_action = "update_cycle"


class UpdateCycleSubAction(BaseAction):
    function_action = "update_cycle_sub"


class DeleteAction(BaseAction):
    function_action = "delete"


class DeleteCycleAction(BaseAction):
    function_action = "delete_cycle"


class DeleteCycleSubAction(BaseAction):
    function_action = "delete_cycle_sub"


class GetParticipantsAction(BaseAction):
    function_action = "get_participants"


class GetVideoAction(BaseAction):
    function_action = "get_video"

class ForceEndAction(BaseAction):
    function_action = "force_end_meeting"
