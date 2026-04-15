#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
"""
Unit tests for get_meeting_status methods in different API implementations.

Tests include:
- TencentGetMeetingStatusTest: Tests for TencentApi.get_meeting_status
- WkGetMeetingStatusTest: Tests for WkApi.get_meeting_status
- ZoomGetMeetingStatusTest: Tests for ZoomApi.get_meeting_status
"""
from unittest import mock
from django.test import TestCase

from meeting.infrastructure.adapter.meeting_adapter_impl.apis.tencent_api import TencentApi
from meeting.infrastructure.adapter.meeting_adapter_impl.apis.wk_api import WkApi
from meeting.infrastructure.adapter.meeting_adapter_impl.apis.zoom_api import ZoomApi
from meeting.infrastructure.adapter.meeting_adapter_impl.actions.tencent_action import (
    TencentGetMeetingStatusAction
)
from meeting.infrastructure.adapter.meeting_adapter_impl.actions.wk_action import (
    WkGetMeetingStatusAction
)
from meeting.infrastructure.adapter.meeting_adapter_impl.actions.zoom_action import (
    ZoomGetMeetingStatusAction
)


class TencentGetMeetingStatusTest(TestCase):
    """Test TencentApi.get_meeting_status method."""

    def setUp(self):
        """Set up test fixtures."""
        self.m_mid = "test_m_mid_123"
        self.action = TencentGetMeetingStatusAction(m_mid=self.m_mid)

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.apis.tencent_api.requests.get')
    @mock.patch.object(TencentApi, '_get_signature')
    def test_get_meeting_status_ongoing(self, mock_signature, mock_get):
        """Test get_meeting_status returns True when meeting is ongoing (status=2)."""
        # Mock signature generation
        mock_signature.return_value = ("test_signature", {"X-TC-Key": "test_key"})

        # Mock successful API response with ongoing status
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "meeting_info_list": [
                {"status": 2}  # status=2 means meeting is ongoing
            ]
        }
        mock_get.return_value = mock_response

        # Create API instance with mocked config
        with mock.patch('django.conf.settings.COMMUNITY_HOST', {
            'test_community': {
                'tencent': [{
                    "HOST": "test_host",
                    "TENCENT_APP_ID": "test_app_id",
                    "TENCENT_SDK_ID": "test_sdk_id",
                    "TENCENT_SECRET_ID": "test_secret_id",
                    "TENCENT_SECRET_KEY": "test_secret_key",
                    "TENCENT_HOST_KEY": "test_host_key"
                }]
            }
        }), mock.patch('django.conf.settings.API_PREFIX', {
            "TENCENT_API_PREFIX": "https://api.tencent.com"
        }), mock.patch('django.conf.settings.REQUEST_TIMEOUT', 30):
            api = TencentApi("test_community", "tencent", "test_host")
            result = api.get_meeting_status(self.action)

        self.assertTrue(result)
        mock_get.assert_called_once()

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.apis.tencent_api.requests.get')
    @mock.patch.object(TencentApi, '_get_signature')
    def test_get_meeting_status_not_ongoing(self, mock_signature, mock_get):
        """Test get_meeting_status returns False when meeting is not ongoing."""
        # Mock signature generation
        mock_signature.return_value = ("test_signature", {"X-TC-Key": "test_key"})

        # Mock successful API response with not-ongoing status (status=1 or 3)
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "meeting_info_list": [
                {"status": 1}  # status=1 means meeting not started
            ]
        }
        mock_get.return_value = mock_response

        # Create API instance with mocked config
        with mock.patch('django.conf.settings.COMMUNITY_HOST', {
            'test_community': {
                'tencent': [{
                    "HOST": "test_host",
                    "TENCENT_APP_ID": "test_app_id",
                    "TENCENT_SDK_ID": "test_sdk_id",
                    "TENCENT_SECRET_ID": "test_secret_id",
                    "TENCENT_SECRET_KEY": "test_secret_key",
                    "TENCENT_HOST_KEY": "test_host_key"
                }]
            }
        }), mock.patch('django.conf.settings.API_PREFIX', {
            "TENCENT_API_PREFIX": "https://api.tencent.com"
        }), mock.patch('django.conf.settings.REQUEST_TIMEOUT', 30):
            api = TencentApi("test_community", "tencent", "test_host")
            result = api.get_meeting_status(self.action)

        self.assertFalse(result)
        mock_get.assert_called_once()

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.apis.tencent_api.requests.get')
    @mock.patch.object(TencentApi, '_get_signature')
    def test_get_meeting_status_api_error(self, mock_signature, mock_get):
        """Test get_meeting_status returns False when API request fails."""
        # Mock signature generation
        mock_signature.return_value = ("test_signature", {"X-TC-Key": "test_key"})

        # Mock failed API response
        mock_response = mock.Mock()
        mock_response.status_code = 500
        mock_response.content = b'{"error": "Internal Server Error"}'
        mock_response.decode = mock.Mock(return_value='{"error": "Internal Server Error"}')
        mock_get.return_value = mock_response

        # Create API instance with mocked config
        with mock.patch('django.conf.settings.COMMUNITY_HOST', {
            'test_community': {
                'tencent': [{
                    "HOST": "test_host",
                    "TENCENT_APP_ID": "test_app_id",
                    "TENCENT_SDK_ID": "test_sdk_id",
                    "TENCENT_SECRET_ID": "test_secret_id",
                    "TENCENT_SECRET_KEY": "test_secret_key",
                    "TENCENT_HOST_KEY": "test_host_key"
                }]
            }
        }), mock.patch('django.conf.settings.API_PREFIX', {
            "TENCENT_API_PREFIX": "https://api.tencent.com"
        }), mock.patch('django.conf.settings.REQUEST_TIMEOUT', 30):
            api = TencentApi("test_community", "tencent", "test_host")
            result = api.get_meeting_status(self.action)

        self.assertFalse(result)
        mock_get.assert_called_once()


class WkGetMeetingStatusTest(TestCase):
    """Test WkApi.get_meeting_status method."""

    def setUp(self):
        """Set up test fixtures."""
        self.mid = "test_mid_123"
        self.action = WkGetMeetingStatusAction(mid=self.mid)

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.apis.wk_api.requests.get')
    @mock.patch.object(WkApi, '_create_proxy_token')
    def test_get_meeting_status_ongoing(self, mock_token, mock_get):
        """Test get_meeting_status returns True when meeting is in online list."""
        # Mock token generation
        mock_token.return_value = "test_access_token"

        # Mock successful API response with meeting in online list
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"conferenceID": self.mid},
                {"conferenceID": "other_meeting_id"}
            ]
        }
        mock_get.return_value = mock_response

        # Create API instance with mocked config
        with mock.patch('django.conf.settings.COMMUNITY_HOST', {
            'test_community': {
                'welink': [{
                    "HOST": "test_host",
                    "ACCOUNT": "test_account",
                    "PWD": "test_pwd"
                }]
            }
        }), mock.patch('django.conf.settings.API_PREFIX', {
            "WELINK_API_PREFIX": "https://api.welink.com"
        }), mock.patch('django.conf.settings.REQUEST_TIMEOUT', 30):
            api = WkApi("test_community", "welink", "test_host")
            result = api.get_meeting_status(self.action)

        self.assertTrue(result)
        mock_get.assert_called_once()

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.apis.wk_api.requests.get')
    @mock.patch.object(WkApi, '_create_proxy_token')
    def test_get_meeting_status_not_ongoing(self, mock_token, mock_get):
        """Test get_meeting_status returns False when meeting is not in online list."""
        # Mock token generation
        mock_token.return_value = "test_access_token"

        # Mock successful API response without target meeting
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {"conferenceID": "other_meeting_id_1"},
                {"conferenceID": "other_meeting_id_2"}
            ]
        }
        mock_get.return_value = mock_response

        # Create API instance with mocked config
        with mock.patch('django.conf.settings.COMMUNITY_HOST', {
            'test_community': {
                'welink': [{
                    "HOST": "test_host",
                    "ACCOUNT": "test_account",
                    "PWD": "test_pwd"
                }]
            }
        }), mock.patch('django.conf.settings.API_PREFIX', {
            "WELINK_API_PREFIX": "https://api.welink.com"
        }), mock.patch('django.conf.settings.REQUEST_TIMEOUT', 30):
            api = WkApi("test_community", "welink", "test_host")
            result = api.get_meeting_status(self.action)

        self.assertFalse(result)
        mock_get.assert_called_once()

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.apis.wk_api.requests.get')
    @mock.patch.object(WkApi, '_create_proxy_token')
    def test_get_meeting_status_api_error(self, mock_token, mock_get):
        """Test get_meeting_status returns None when API request fails."""
        # Mock token generation
        mock_token.return_value = "test_access_token"

        # Mock failed API response
        mock_response = mock.Mock()
        mock_response.status_code = 500
        mock_response.json.return_value = {"error": "Internal Server Error"}
        mock_get.return_value = mock_response

        # Create API instance with mocked config
        with mock.patch('django.conf.settings.COMMUNITY_HOST', {
            'test_community': {
                'welink': [{
                    "HOST": "test_host",
                    "ACCOUNT": "test_account",
                    "PWD": "test_pwd"
                }]
            }
        }), mock.patch('django.conf.settings.API_PREFIX', {
            "WELINK_API_PREFIX": "https://api.welink.com"
        }), mock.patch('django.conf.settings.REQUEST_TIMEOUT', 30):
            api = WkApi("test_community", "welink", "test_host")
            result = api.get_meeting_status(self.action)

        self.assertIsNone(result)
        mock_get.assert_called_once()


class ZoomGetMeetingStatusTest(TestCase):
    """Test ZoomApi.get_meeting_status method."""

    def setUp(self):
        """Set up test fixtures."""
        self.mid = "test_mid_123"
        self.action = ZoomGetMeetingStatusAction(mid=self.mid)

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.apis.zoom_api.requests.get')
    @mock.patch.object(ZoomApi, '_get_oauth_token')
    def test_get_meeting_status_ongoing(self, mock_token, mock_get):
        """Test get_meeting_status returns True when meeting status is 'started'."""
        # Mock OAuth token generation
        mock_token.return_value = "test_oauth_token"

        # Mock successful API response with started status
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "started"  # started means meeting is ongoing
        }
        mock_get.return_value = mock_response

        # Create API instance with mocked config
        with mock.patch('django.conf.settings.COMMUNITY_HOST', {
            'test_community': {
                'zoom': [{
                    "HOST": "test_host",
                    "ACCOUNT": "test_account"
                }]
            }
        }), mock.patch('django.conf.settings.API_PREFIX', {
            "ZOOM_API_PREFIX": "https://api.zoom.us"
        }), mock.patch('django.conf.settings.COMMUNITY_ZOOM_OBS', {
            'test_community': {
                "AK": "test_ak",
                "SK": "test_sk",
                "ENDPOINT": "test_endpoint",
                "BUCKET": "test_bucket",
                "OBJECT": "test_object"
            }
        }), mock.patch('django.conf.settings.REQUEST_TIMEOUT', 30), \
             mock.patch('django.conf.settings.BILI_UPLOAD_DATE', 7), \
             mock.patch('django.conf.settings.BILI_VIDEO_MIN_SIZE', 1024):
            api = ZoomApi("test_community", "zoom", "test_host")
            result = api.get_meeting_status(self.action)

        self.assertTrue(result)
        mock_get.assert_called_once()

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.apis.zoom_api.requests.get')
    @mock.patch.object(ZoomApi, '_get_oauth_token')
    def test_get_meeting_status_not_ongoing(self, mock_token, mock_get):
        """Test get_meeting_status returns False when meeting status is not 'started'."""
        # Mock OAuth token generation
        mock_token.return_value = "test_oauth_token"

        # Mock successful API response with waiting/ended status
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "waiting"  # waiting means meeting not started yet
        }
        mock_get.return_value = mock_response

        # Create API instance with mocked config
        with mock.patch('django.conf.settings.COMMUNITY_HOST', {
            'test_community': {
                'zoom': [{
                    "HOST": "test_host",
                    "ACCOUNT": "test_account"
                }]
            }
        }), mock.patch('django.conf.settings.API_PREFIX', {
            "ZOOM_API_PREFIX": "https://api.zoom.us"
        }), mock.patch('django.conf.settings.COMMUNITY_ZOOM_OBS', {
            'test_community': {
                "AK": "test_ak",
                "SK": "test_sk",
                "ENDPOINT": "test_endpoint",
                "BUCKET": "test_bucket",
                "OBJECT": "test_object"
            }
        }), mock.patch('django.conf.settings.REQUEST_TIMEOUT', 30), \
             mock.patch('django.conf.settings.BILI_UPLOAD_DATE', 7), \
             mock.patch('django.conf.settings.BILI_VIDEO_MIN_SIZE', 1024):
            api = ZoomApi("test_community", "zoom", "test_host")
            result = api.get_meeting_status(self.action)

        self.assertFalse(result)
        mock_get.assert_called_once()

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.apis.zoom_api.requests.get')
    @mock.patch.object(ZoomApi, '_get_oauth_token')
    def test_get_meeting_status_api_error(self, mock_token, mock_get):
        """Test get_meeting_status returns False when API request fails."""
        # Mock OAuth token generation
        mock_token.return_value = "test_oauth_token"

        # Mock failed API response
        mock_response = mock.Mock()
        mock_response.status_code = 404
        mock_response.content = b'{"message": "Meeting not found"}'
        mock_response.decode = mock.Mock(return_value='{"message": "Meeting not found"}')
        mock_get.return_value = mock_response

        # Create API instance with mocked config
        with mock.patch('django.conf.settings.COMMUNITY_HOST', {
            'test_community': {
                'zoom': [{
                    "HOST": "test_host",
                    "ACCOUNT": "test_account"
                }]
            }
        }), mock.patch('django.conf.settings.API_PREFIX', {
            "ZOOM_API_PREFIX": "https://api.zoom.us"
        }), mock.patch('django.conf.settings.COMMUNITY_ZOOM_OBS', {
            'test_community': {
                "AK": "test_ak",
                "SK": "test_sk",
                "ENDPOINT": "test_endpoint",
                "BUCKET": "test_bucket",
                "OBJECT": "test_object"
            }
        }), mock.patch('django.conf.settings.REQUEST_TIMEOUT', 30), \
             mock.patch('django.conf.settings.BILI_UPLOAD_DATE', 7), \
             mock.patch('django.conf.settings.BILI_VIDEO_MIN_SIZE', 1024):
            api = ZoomApi("test_community", "zoom", "test_host")
            result = api.get_meeting_status(self.action)

        self.assertFalse(result)
        mock_get.assert_called_once()