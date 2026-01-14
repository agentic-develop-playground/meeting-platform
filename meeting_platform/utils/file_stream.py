#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
import stat
import os
import requests

from django.conf import settings


def write_content(path, content, model="wb"):
    flags = os.O_CREAT | os.O_WRONLY
    modes = stat.S_IWUSR | stat.S_IRUSR
    with os.fdopen(os.open(path, flags, modes), model) as f:
        result = f.write(content)
    return result


def read_content(path):
    with open(path, 'r', encoding='utf-8') as fp:
        return fp.read()


def download_big_file(url, path, headers=None, model="wb"):
    r = requests.get(url, headers=headers, stream=True, timeout=settings.REQUEST_TIMEOUT)
    flags = os.O_CREAT | os.O_WRONLY
    modes = stat.S_IWUSR | stat.S_IRUSR
    with os.fdopen(os.open(path, flags, modes), model) as f:
        for chunk in r.iter_content(chunk_size=4096):
            if chunk:
                f.write(chunk)
                f.flush()
    return path
