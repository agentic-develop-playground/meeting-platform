#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.

from rest_framework import pagination
from rest_framework.response import Response
from collections import OrderedDict


class MyPagination(pagination.PageNumberPagination):
    page_size = 10
    max_page_size = 50
    page_size_query_param = "size"

    def _calc_get_page_number(self, request):
        return request.query_params.get(self.page_query_param, 1)

    def get_paginated_response(self, data):
        page_size = self.get_page_size(self.request)
        page_num = self._calc_get_page_number(self.request)
        return Response(OrderedDict([
            ('total', self.page.paginator.count),
            ('page', page_num),
            ('size', page_size),
            ('data', data)
        ]))
