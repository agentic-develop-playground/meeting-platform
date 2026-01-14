#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.

from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class MyAnonRateThrottle(AnonRateThrottle):
    def get_ident(self, request):
        return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR")


class MyUserRateThrottle(UserRateThrottle):
    def get_ident(self, request):
        return request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR")
