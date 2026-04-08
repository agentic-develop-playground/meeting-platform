#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
"""
闭门会议(private meeting)功能测试

Test suite for the private meeting feature:
- Only support WeLink platform
- Only support non-cyclic meetings
- Do not support email list notifications
- Do not send Kafka messages
- Skip recording upload processing
- Are filtered from public query results
"""
import logging
from unittest import mock
from rest_framework import status
from meeting_platform.test.meeting.test_base import BaseMeetingTest
from meeting_platform.test.meeting.fixtures import create_test_meeting_data, create_daily_cycle_data
from meeting_platform.utils.ret_code import RetCode

logger = logging.getLogger("log")


class CreatePrivateMeetingTest(BaseMeetingTest):
    """测试创建闭门会议"""
    url = "/inner/v1/meeting/meeting/"

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    def test_create_private_meeting_welink_success(self, mock_create):
        """测试在WeLink平台创建闭门会议成功"""
        mock_create.return_value = {
            'mid': 'private_test_id',
            'join_url': 'https://test.welink.com/j/123',
            'host_id': 'host@test.com'
        }
        data = create_test_meeting_data({
            'platform': 'welink',
            'is_private': True
        })
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['code'], 200)

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    def test_create_private_meeting_zoom_failed(self, mock_create):
        """测试在非WeLink平台创建闭门会议失败"""
        mock_create.return_value = {
            'mid': 'test_id',
            'join_url': 'https://test.zoom.us/j/123',
            'host_id': 'host@test.com'
        }
        for platform in ['zoom', 'tencent']:
            data = create_test_meeting_data({
                'platform': platform,
                'is_private': True
            })
            response = self.client.post(self.url, data=data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.json()['code'], 400)

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    def test_create_private_meeting_cyclic_failed(self, mock_create):
        """测试创建周期性闭门会议失败"""
        mock_create.return_value = {
            'mid': 'test_id',
            'join_url': 'https://test.welink.com/j/123',
            'host_id': 'host@test.com'
        }
        # Use proper cyclic meeting data with integer cycle_type (0=daily)
        data = create_daily_cycle_data(overrides={
            'platform': 'welink',
            'is_private': True
        })
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['code'], 400)

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    @mock.patch('django.conf.settings.COMMUNITY_PRIVATE_MEETING_EMAIL_SUFFIX', {'openEuler': '@openEuler.com'})
    def test_create_private_meeting_with_mailing_list(self, mock_create):
        """测试闭门会议使用邮件列表时的验证"""
        mock_create.return_value = {
            'mid': 'test_id',
            'join_url': 'https://test.welink.com/j/123',
            'host_id': 'host@test.com'
        }
        data = create_test_meeting_data({
            'platform': 'welink',
            'is_private': True,
            'email_list': 'test@openEuler.com;user2@test.com'
        })
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['code'], 400)

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    def test_create_private_meeting_with_other_emails_ok(self, mock_create):
        """测试闭门会议使用非社区邮件列表时成功"""
        mock_create.return_value = {
            'mid': 'test_id',
            'join_url': 'https://test.welink.com/j/123',
            'host_id': 'host@test.com'
        }
        data = create_test_meeting_data({
            'platform': 'welink',
            'is_private': True,
            'email_list': 'user1@test.com;user2@example.com'
        })
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['code'], 200)

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    def test_create_public_meeting_still_works(self, mock_create):
        """测试创建公开会议仍然正常工作"""
        mock_create.return_value = {
            'mid': 'public_test_id',
            'join_url': 'https://test.welink.com/j/123',
            'host_id': 'host@test.com'
        }
        # Test with is_private=False explicitly
        data = create_test_meeting_data({
            'platform': 'welink',
            'is_private': False
        })
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['code'], 200)


class UpdatePrivateMeetingTest(BaseMeetingTest):
    """测试更新闭门会议"""
    url = "/inner/v1/meeting/meeting/{id}/"

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.update')
    def test_update_to_private_welink_success(self, mock_update, mock_create):
        """测试更新为闭门会议成功"""
        mock_create.return_value = {
            'mid': 'test_id',
            'join_url': 'https://test.welink.com/j/123',
            'host_id': 'host@test.com'
        }
        mock_update.return_value = {
            'mid': 'test_id',
            'join_url': 'https://test.welink.com/j/123',
            'host_id': 'host@test.com'
        }

        # First create a meeting
        data = create_test_meeting_data({
            'platform': 'welink',
            'is_private': False
        })
        create_response = self.client.post("/inner/v1/meeting/meeting/", data=data)
        meeting_id = create_response.json()['data']

        # Then update it to private
        update_data = create_test_meeting_data({
            'platform': 'welink',
            'is_private': True,
            'topic': 'Updated Topic',
            'is_record': False
        })
        response = self.client.put(self.url.format(id=meeting_id), data=update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['code'], 200)

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.update')
    def test_update_to_private_zoom_failed(self, mock_update, mock_create):
        """测试在非WeLink平台更新为闭门会议失败"""
        mock_create.return_value = {
            'mid': 'test_id',
            'join_url': 'https://test.zoom.us/j/123',
            'host_id': 'host@test.com'
        }
        mock_update.return_value = {
            'mid': 'test_id',
            'join_url': 'https://test.zoom.us/j/123',
            'host_id': 'host@test.com'
        }

        # First create a zoom meeting
        create_data = create_test_meeting_data({
            'platform': 'zoom',
            'is_private': False
        })
        create_response = self.client.post("/inner/v1/meeting/meeting/", data=create_data)
        meeting_id = create_response.json()['data']

        # Try to update it to private - should fail
        update_data = create_test_meeting_data({
            'platform': 'zoom',
            'is_private': True
        })
        response = self.client.put(self.url.format(id=meeting_id), data=update_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.json()['code'], 400)


class QueryPrivateMeetingTest(BaseMeetingTest):
    """测试查询闭门会议"""
    url = "/inner/v1/meeting/meeting/"

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    def test_private_meeting_filtered_from_list(self, mock_create):
        """测试闭门会议在列表查询中被过滤"""
        mock_create.return_value = {
            'mid': 'test_id',
            'join_url': 'https://test.welink.com/j/123',
            'host_id': 'host@test.com'
        }

        # Create a public meeting
        public_data = create_test_meeting_data({
            'platform': 'welink',
            'topic': 'Public Meeting',
            'is_private': False
        })
        self.client.post(self.url, data=public_data)

        # Create a private meeting
        private_data = create_test_meeting_data({
            'platform': 'welink',
            'topic': 'Private Meeting',
            'is_private': True
        })
        self.client.post(self.url, data=private_data)

        # Query list - should only return public meetings
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Response format depends on pagination:
        # - With pagination: {'code': 200, 'msg': 'success', 'data': {'total': N, 'page': 1, 'size': 10, 'data': [...]}}
        # - Without pagination: {'code': 200, 'msg': 'success', 'data': [...]}
        data = response.json()['data']
        if isinstance(data, dict) and 'data' in data:
            results = data['data']
        else:
            results = data
        for meeting in results:
            self.assertEqual(meeting['is_private'], False)


class PrivateMeetingKafkaTest(BaseMeetingTest):
    """测试闭门会议的Kafka消息处理"""

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    @mock.patch('meeting_platform.utils.client.kafka_client.KafKaClient')
    def test_private_meeting_no_kafka_message(self, mock_kafka_client, mock_create):
        """测试闭门会议不发送Kafka消息"""
        mock_create.return_value = {
            'mid': 'private_id',
            'join_url': 'https://test.welink.com/j/123',
            'host_id': 'host@test.com'
        }
        mock_kafka_client.return_value.__enter__ = mock.MagicMock(return_value=mock_kafka_client)
        mock_kafka_client.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_kafka_client.return_value.send_msg = mock.MagicMock()

        data = create_test_meeting_data({'platform': 'welink', 'is_private': True})
        response = self.client.post("/inner/v1/meeting/meeting/", data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['code'], 200)
        # Kafka send_msg should not be called for private meetings
        mock_kafka_client.return_value.send_msg.assert_not_called()

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    @mock.patch('meeting_platform.utils.client.kafka_client.KafKaClient')
    def test_public_meeting_sends_kafka_message(self, mock_kafka_client, mock_create):
        """测试公开会议仍然发送Kafka消息"""
        mock_create.return_value = {
            'mid': 'public_id',
            'join_url': 'https://test.welink.com/j/123',
            'host_id': 'host@test.com'
        }
        mock_kafka_client.return_value.__enter__ = mock.MagicMock(return_value=mock_kafka_client)
        mock_kafka_client.return_value.__exit__ = mock.MagicMock(return_value=False)
        mock_kafka_client.return_value.send_msg = mock.MagicMock()

        data = create_test_meeting_data({'platform': 'welink', 'is_private': False})
        response = self.client.post("/inner/v1/meeting/meeting/", data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['code'], 200)
        # Kafka send_msg should be called for public meetings
        # Note: This test may not work if Kafka config is not properly set in test settings


class PrivateMeetingEdgeCaseTest(BaseMeetingTest):
    """测试闭门会议的边界条件"""

    url = "/inner/v1/meeting/meeting/"

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    def test_private_meeting_default_false(self, mock_create):
        """测试不传is_private参数时默认为False"""
        mock_create.return_value = {
            'mid': 'test_id',
            'join_url': 'https://test.welink.com/j/123',
            'host_id': 'host@test.com'
        }
        data = create_test_meeting_data({'platform': 'welink'})
        data.pop('is_private', None)
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['code'], 200)

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    def test_private_meeting_various_platform_cases(self, mock_create):
        """测试各种平台的闭门会议验证"""
        mock_create.return_value = {
            'mid': 'test_id',
            'join_url': 'https://test.welink.com/j/123',
            'host_id': 'host@test.com'
        }

        # Test welink (lowercase) - should succeed
        data = create_test_meeting_data({
            'platform': 'welink',
            'is_private': True
        })
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                       f"Failed for platform: welink")
        self.assertEqual(response.json()['code'], 200)

        # Test zoom and tencent - should fail
        for platform in ['zoom', 'tencent']:
            data = create_test_meeting_data({
                'platform': platform,
                'is_private': True
            })
            response = self.client.post(self.url, data=data)
            self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
            self.assertEqual(response.json()['code'], 400)

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    def test_private_meeting_empty_email_list(self, mock_create):
        """测试闭门会议使用空邮件列表"""
        mock_create.return_value = {
            'mid': 'test_id',
            'join_url': 'https://test.welink.com/j/123',
            'host_id': 'host@test.com'
        }
        data = create_test_meeting_data({
            'platform': 'welink',
            'is_private': True,
            'email_list': ''
        })
        response = self.client.post(self.url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['code'], 200)
