#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
import logging
from django.http.response import HttpResponseBase
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger("log")


# noinspection PyMethodMayBeStatic
class MyMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        if isinstance(response, HttpResponseBase):
            response["X-XSS-Protection"] = "1; mode=block"
            response["X-Frame-Options"] = "DENY"
            response["X-Content-Type-Options"] = "nosniff"
            response["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response["Content-Security-Policy"] = "script-src 'self'; object-src 'none'; frame-src 'none'"
            response["Cache-Control"] = "no-cache,no-store,must-revalidate"
            response["Pragma"] = "no-cache"
            response["Expires"] = 0
            response["Referrer-Policy"] = "no-referrer"

        logger.info("[{}] {} {} => {}".format(
            str(request.META.get("REMOTE_ADDR")),
            request.method,
            str(request.META.get("RAW_URI")),
            response.status_code
        ))
        return response
