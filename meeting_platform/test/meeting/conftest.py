#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
"""
Conftest for meeting tests - mocks kafka module to prevent import errors in Python 3.13.

The kafka-python package has compatibility issues with Python 3.13 due to the six module.
This conftest mocks kafka before any imports that would trigger the error.
"""
import sys
from unittest.mock import MagicMock

# Mock kafka module before any imports
sys.modules['kafka'] = MagicMock()
sys.modules['kafka.vendor'] = MagicMock()
sys.modules['kafka.vendor.six'] = MagicMock()
sys.modules['kafka.vendor.six.moves'] = MagicMock()
sys.modules['kafka.consumer'] = MagicMock()
sys.modules['kafka.producer'] = MagicMock()

# Mock KafkaProducer class
mock_producer = MagicMock()
sys.modules['kafka'].KafkaProducer = mock_producer