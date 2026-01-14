#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
from obs import ObsClient

from meeting.domain.repository.obs_adapter import ObsAdapter

from meeting_platform.utils.client.obs_client import MyObsClient


class ObsAdapterImp(MyObsClient, ObsAdapter):
    pass
