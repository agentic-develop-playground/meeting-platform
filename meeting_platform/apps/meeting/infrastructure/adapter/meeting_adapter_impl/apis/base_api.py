#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.

import importlib
import inspect
import os
import pkgutil
import sys

from django.conf import settings


class _ApiMods:
    _mod_list = list()

    @classmethod
    def _get_mods(cls):
        if not cls._mod_list:
            apis_path = os.path.join(settings.BASE_DIR, "apps", "meeting", "infrastructure", "adapter",
                                     "meeting_adapter_impl", "apis")
            meeting_apis_path = os.path.dirname(apis_path)
            if meeting_apis_path not in sys.path:
                sys.path.append(meeting_apis_path)
            cls._mod_list = [mod for _, mod, _ in pkgutil.iter_modules([apis_path])]
        return cls._mod_list

    @property
    def get_mods(self):
        return self._get_mods()


def handler_meeting(community, platform, host_id, action):
    mods = _ApiMods().get_mods
    for mod_name in mods:
        if mod_name == "base_api":
            continue
        mod = importlib.import_module(".apis.{}".format(mod_name),
                                      package="meeting_platform.apps.meeting.infrastructure.adapter."
                                              "meeting_adapter_impl")
        for _, cls in mod.__dict__.items():
            if not inspect.isclass(cls):
                continue
            if str(cls.__dict__.get("meeting_type")).lower() != platform.lower():
                continue
            instance = cls(community, platform, host_id)
            if not hasattr(instance, action.function_action):
                raise RuntimeError("class/{} must have the action attribute/{}".
                                   format(str(cls), str(action.function_action)))
            fun = getattr(instance, action.function_action)
            return fun(action)
