#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
from rest_framework import mixins
from rest_framework.generics import RetrieveAPIView, GenericAPIView

from meeting_platform.utils.ret_api import ret_json
from meeting_platform.utils.customized.my_serializers import EmptySerializers


class EmptyAPIView:
    """自定义使用空的序列化器的视图"""
    serializer_class = EmptySerializers

    def get_queryset(self):
        """get_queryset will return empty list"""
        return list()


# noinspection PyUnresolvedReferences
class MyListModelMixin:
    """
    List a queryset.
    """

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return ret_json(data=serializer.data)


# noinspection PyUnresolvedReferences
class MyRetrieveModelMixin:
    """
    Retrieve a model instance.
    """

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return ret_json(data=serializer.data)


class MyUpdateAPIView(mixins.UpdateModelMixin,
                      GenericAPIView):
    """
    Concrete view for updating a model instance.
    """

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)


class PingView(GenericAPIView):
    """get the heartbeat"""

    def get(self, request, *args, **kwargs):
        """get the status of service"""
        return ret_json(msg='the status is ok')
