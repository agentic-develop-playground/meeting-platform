#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
"""
Pytest configuration file for Django tests.
This file configures Django settings and Python paths for pytest to work correctly.
"""
import os
import sys

# Get the project root directory (where manage.py is located)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
# Get the meeting_platform directory
MEETING_PLATFORM_DIR = os.path.join(PROJECT_ROOT, 'meeting_platform')
# Get the apps directory
APPS_DIR = os.path.join(MEETING_PLATFORM_DIR, 'apps')

# Add paths to sys.path so that imports work correctly
if MEETING_PLATFORM_DIR not in sys.path:
    sys.path.insert(0, MEETING_PLATFORM_DIR)
if APPS_DIR not in sys.path:
    sys.path.insert(0, APPS_DIR)

# Set Django settings module - pytest-django will handle the setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'meeting_platform.settings.test')