#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.

from rest_framework.serializers import Serializer


# noinspection PyAbstractClass
class EmptySerializers(Serializer):
    """Nothing to do in EmptySerializers"""
    pass


# noinspection PyUnresolvedReferences
class MySerializerParse:
    def get_my_serializer_data(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data
