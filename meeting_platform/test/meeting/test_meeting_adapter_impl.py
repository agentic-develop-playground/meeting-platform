#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
"""
Unit tests for meeting_adapter_impl.py.

Tests include:
- MeetingAction static methods for different platforms
- MeetingAdapterImpl methods with mocked handler_meeting
"""
from unittest import mock
from django.test import TestCase

from meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl import (
    MeetingAction, MeetingAdapterImpl
)
from meeting.infrastructure.adapter.meeting_adapter_impl.actions.tencent_action import (
    TencentCreateAction, TencentUpdateAction, TencentDeleteAction,
    TencentGetParticipantsAction, TencentGetVideo, TencentForceEndAction,
    TencentGetMeetingStatusAction
)
from meeting.infrastructure.adapter.meeting_adapter_impl.actions.wk_action import (
    WkCreateAction, WkUpdateAction, WkDeleteAction,
    WkGetParticipantsAction, WkGetVideo, WkCreateCycleAction,
    WkUpdateCycleAction, WkDeleteCycleAction, WkUpdateCycleSubAction,
    WkDeleteCycleSubAction, WkForceEndAction, WkGetMeetingStatusAction
)
from meeting.infrastructure.adapter.meeting_adapter_impl.actions.zoom_action import (
    ZoomCreateAction, ZoomUpdateAction, ZoomDeleteAction,
    ZoomGetParticipantsAction, ZoomGetVideo, ZoomForceEndAction,
    ZoomGetMeetingStatusAction
)
from meeting.domain.primitive.cycle_type import CycleType
from meeting_platform.utils.ret_code import RetCode
from meeting_platform.utils.ret_api import MyInnerError


class MeetingActionGetCreateActionTest(TestCase):
    """Test MeetingAction.get_create_action for different platforms."""

    def test_tencent_create_action(self):
        """Test get_create_action returns TencentCreateAction for tencent platform."""
        meeting = {
            "date": "2026-01-15",
            "start": "10:00",
            "end": "11:00",
            "topic": "Test Meeting",
            "is_record": False,
        }
        action = MeetingAction.get_create_action("tencent", meeting)
        self.assertIsInstance(action, TencentCreateAction)
        self.assertEqual(action.date, "2026-01-15")
        self.assertEqual(action.start, "10:00")
        self.assertEqual(action.end, "11:00")

    def test_wk_create_action_non_cycle(self):
        """Test get_create_action returns WkCreateAction for welink non-cycle meeting."""
        meeting = {
            "date": "2026-01-15",
            "start": "10:00",
            "end": "11:00",
            "topic": "Test Meeting",
            "is_private": False,
            "is_record": False,
            "is_cycle": False,
        }
        action = MeetingAction.get_create_action("welink", meeting)
        self.assertIsInstance(action, WkCreateAction)
        self.assertEqual(action.date, "2026-01-15")
        self.assertEqual(action.topic, "Test Meeting")

    def test_wk_create_action_cycle(self):
        """Test get_create_action returns WkCreateCycleAction for welink cycle meeting."""
        meeting = {
            "cycle_start_date": "2026-01-15",
            "cycle_end_date": "2026-02-15",
            "cycle_start": "10:00",
            "cycle_end": "11:00",
            "cycle_type": CycleType.Week,
            "cycle_interval": 1,
            "cycle_point": ["MON"],
            "topic": "Cycle Meeting",
            "is_record": False,
            "is_cycle": True,
        }
        action = MeetingAction.get_create_action("welink", meeting)
        self.assertIsInstance(action, WkCreateCycleAction)
        self.assertEqual(action.topic, "Cycle Meeting")
        self.assertEqual(action.cycle_type, "Week")

    def test_zoom_create_action(self):
        """Test get_create_action returns ZoomCreateAction for zoom platform."""
        meeting = {
            "date": "2026-01-15",
            "start": "10:00",
            "end": "11:00",
            "topic": "Zoom Meeting",
            "is_record": True,
        }
        action = MeetingAction.get_create_action("zoom", meeting)
        self.assertIsInstance(action, ZoomCreateAction)
        self.assertEqual(action.date, "2026-01-15")
        self.assertEqual(action.is_record, True)

    def test_invalid_platform_raises_runtime_error(self):
        """Test get_create_action raises RuntimeError for invalid platform."""
        meeting = {
            "date": "2026-01-15",
            "start": "10:00",
            "end": "11:00",
            "topic": "Test",
            "is_record": False,
        }
        with self.assertRaises(RuntimeError) as context:
            MeetingAction.get_create_action("invalid_platform", meeting)
        self.assertIn("invalid platform type", str(context.exception))


class MeetingActionGetUpdateActionTest(TestCase):
    """Test MeetingAction.get_update_action for different platforms."""

    def test_tencent_update_action(self):
        """Test get_update_action returns TencentUpdateAction for tencent platform."""
        meeting = {
            "mid": "tencent_mid_123",
            "m_mid": "m_mid_123",
            "date": "2026-01-15",
            "start": "10:00",
            "end": "11:00",
            "topic": "Updated Meeting",
            "is_record": False,
        }
        action = MeetingAction.get_update_action("tencent", meeting)
        self.assertIsInstance(action, TencentUpdateAction)
        self.assertEqual(action.mid, "tencent_mid_123")
        self.assertEqual(action.m_mid, "m_mid_123")

    def test_wk_update_action_non_cycle(self):
        """Test get_update_action returns WkUpdateAction for welink non-cycle meeting."""
        meeting = {
            "mid": "wk_mid_123",
            "date": "2026-01-15",
            "start": "10:00",
            "end": "11:00",
            "topic": "Updated Meeting",
            "is_private": False,
            "is_record": False,
            "is_cycle": False,
        }
        action = MeetingAction.get_update_action("welink", meeting)
        self.assertIsInstance(action, WkUpdateAction)
        self.assertEqual(action.mid, "wk_mid_123")

    def test_wk_update_action_cycle(self):
        """Test get_update_action returns WkUpdateCycleAction for welink cycle meeting."""
        meeting = {
            "mid": "wk_cycle_mid",
            "cycle_start_date": "2026-01-15",
            "cycle_end_date": "2026-02-15",
            "cycle_start": "10:00",
            "cycle_end": "11:00",
            "cycle_type": CycleType.DAY,
            "cycle_interval": 2,
            "topic": "Updated Cycle Meeting",
            "is_record": False,
            "is_cycle": True,
        }
        action = MeetingAction.get_update_action("welink", meeting)
        self.assertIsInstance(action, WkUpdateCycleAction)
        self.assertEqual(action.mid, "wk_cycle_mid")

    def test_zoom_update_action(self):
        """Test get_update_action returns ZoomUpdateAction for zoom platform."""
        meeting = {
            "mid": "zoom_mid_123",
            "date": "2026-01-15",
            "start": "10:00",
            "end": "11:00",
            "topic": "Updated Zoom Meeting",
            "is_record": False,
        }
        action = MeetingAction.get_update_action("zoom", meeting)
        self.assertIsInstance(action, ZoomUpdateAction)
        self.assertEqual(action.mid, "zoom_mid_123")

    def test_invalid_platform_raises_runtime_error(self):
        """Test get_update_action raises RuntimeError for invalid platform."""
        meeting = {
            "mid": "test_mid",
            "date": "2026-01-15",
            "start": "10:00",
            "end": "11:00",
            "topic": "Test",
            "is_record": False,
        }
        with self.assertRaises(RuntimeError) as context:
            MeetingAction.get_update_action("invalid_platform", meeting)
        self.assertIn("invalid platform type", str(context.exception))


class MeetingActionGetUpdateSubActionTest(TestCase):
    """Test MeetingAction.get_update_sub_action."""

    def test_wk_update_sub_action(self):
        """Test get_update_sub_action returns WkUpdateCycleSubAction for welink."""
        meeting = {
            "mid": "wk_cycle_mid",
            "sub_id": "sub_001",
            "date": "2026-01-15",
            "start": "10:00",
            "end": "11:00",
        }
        action = MeetingAction.get_update_sub_action("welink", meeting)
        self.assertIsInstance(action, WkUpdateCycleSubAction)
        self.assertEqual(action.mid, "wk_cycle_mid")
        self.assertEqual(action.sub_id, "sub_001")

    def test_invalid_platform_raises_runtime_error(self):
        """Test get_update_sub_action raises RuntimeError for non-welink platform."""
        meeting = {
            "mid": "test_mid",
            "sub_id": "sub_001",
            "date": "2026-01-15",
            "start": "10:00",
            "end": "11:00",
        }
        with self.assertRaises(RuntimeError) as context:
            MeetingAction.get_update_sub_action("zoom", meeting)
        self.assertIn("invalid platform type", str(context.exception))


class MeetingActionGetDeleteActionTest(TestCase):
    """Test MeetingAction.get_delete_action for different platforms."""

    def test_tencent_delete_action(self):
        """Test get_delete_action returns TencentDeleteAction for tencent platform."""
        meeting = {
            "mid": "tencent_mid",
            "m_mid": "m_mid_123",
        }
        action = MeetingAction.get_delete_action("tencent", meeting)
        self.assertIsInstance(action, TencentDeleteAction)
        self.assertEqual(action.mid, "tencent_mid")

    def test_wk_delete_action_non_cycle(self):
        """Test get_delete_action returns WkDeleteAction for welink non-cycle meeting."""
        meeting = {
            "mid": "wk_mid",
            "is_cycle": False,
        }
        action = MeetingAction.get_delete_action("welink", meeting)
        self.assertIsInstance(action, WkDeleteAction)
        self.assertEqual(action.mid, "wk_mid")

    def test_wk_delete_action_cycle(self):
        """Test get_delete_action returns WkDeleteCycleAction for welink cycle meeting."""
        meeting = {
            "mid": "wk_cycle_mid",
            "is_cycle": True,
        }
        action = MeetingAction.get_delete_action("welink", meeting)
        self.assertIsInstance(action, WkDeleteCycleAction)
        self.assertEqual(action.mid, "wk_cycle_mid")

    def test_zoom_delete_action(self):
        """Test get_delete_action returns ZoomDeleteAction for zoom platform."""
        meeting = {
            "mid": "zoom_mid",
        }
        action = MeetingAction.get_delete_action("zoom", meeting)
        self.assertIsInstance(action, ZoomDeleteAction)
        self.assertEqual(action.mid, "zoom_mid")

    def test_invalid_platform_raises_runtime_error(self):
        """Test get_delete_action raises RuntimeError for invalid platform."""
        meeting = {"mid": "test_mid"}
        with self.assertRaises(RuntimeError) as context:
            MeetingAction.get_delete_action("invalid", meeting)
        self.assertIn("invalid platform type", str(context.exception))


class MeetingActionGetDeleteSubActionTest(TestCase):
    """Test MeetingAction.get_delete_sub_action."""

    def test_wk_delete_sub_action(self):
        """Test get_delete_sub_action returns WkDeleteCycleSubAction for welink."""
        meeting = {
            "mid": "wk_cycle_mid",
            "sub_id": "sub_001",
        }
        action = MeetingAction.get_delete_sub_action("welink", meeting)
        self.assertIsInstance(action, WkDeleteCycleSubAction)
        self.assertEqual(action.mid, "wk_cycle_mid")
        self.assertEqual(action.sub_id, "sub_001")

    def test_invalid_platform_raises_runtime_error(self):
        """Test get_delete_sub_action raises RuntimeError for non-welink platform."""
        meeting = {
            "mid": "test_mid",
            "sub_id": "sub_001",
        }
        with self.assertRaises(RuntimeError) as context:
            MeetingAction.get_delete_sub_action("tencent", meeting)
        self.assertIn("invalid platform type", str(context.exception))


class MeetingActionGetParticipantsActionTest(TestCase):
    """Test MeetingAction.get_participants_action for different platforms."""

    def test_tencent_get_participants_action(self):
        """Test get_participants_action returns TencentGetParticipantsAction."""
        meeting = {"m_mid": "m_mid_123"}
        action = MeetingAction.get_participants_action("tencent", meeting)
        self.assertIsInstance(action, TencentGetParticipantsAction)
        self.assertEqual(action.m_mid, "m_mid_123")

    def test_wk_get_participants_action(self):
        """Test get_participants_action returns WkGetParticipantsAction."""
        meeting = {
            "mid": "wk_mid",
            "date": "2026-01-15",
            "start": "10:00",
            "end": "11:00",
        }
        action = MeetingAction.get_participants_action("welink", meeting)
        self.assertIsInstance(action, WkGetParticipantsAction)
        self.assertEqual(action.mid, "wk_mid")

    def test_zoom_get_participants_action(self):
        """Test get_participants_action returns ZoomGetParticipantsAction."""
        meeting = {"mid": "zoom_mid"}
        action = MeetingAction.get_participants_action("zoom", meeting)
        self.assertIsInstance(action, ZoomGetParticipantsAction)
        self.assertEqual(action.mid, "zoom_mid")

    def test_invalid_platform_raises_runtime_error(self):
        """Test get_participants_action raises RuntimeError for invalid platform."""
        meeting = {"mid": "test_mid"}
        with self.assertRaises(RuntimeError) as context:
            MeetingAction.get_participants_action("invalid", meeting)
        self.assertIn("invalid platform type", str(context.exception))


class MeetingActionGetVideoActionTest(TestCase):
    """Test MeetingAction.get_video_action for different platforms."""

    def test_tencent_get_video_action(self):
        """Test get_video_action returns TencentGetVideo."""
        meeting = {
            "mid": "tencent_mid",
            "m_mid": "m_mid",
            "date": "2026-01-15",
            "start": "10:00",
        }
        action = MeetingAction.get_video_action("tencent", meeting)
        self.assertIsInstance(action, TencentGetVideo)
        self.assertEqual(action.mid, "tencent_mid")

    def test_wk_get_video_action(self):
        """Test get_video_action returns WkGetVideo."""
        meeting = {
            "mid": "wk_mid",
            "date": "2026-01-15",
            "start": "10:00",
            "end": "11:00",
        }
        action = MeetingAction.get_video_action("welink", meeting)
        self.assertIsInstance(action, WkGetVideo)
        self.assertEqual(action.mid, "wk_mid")

    def test_zoom_get_video_action(self):
        """Test get_video_action returns ZoomGetVideo."""
        meeting = {"mid": "zoom_mid"}
        action = MeetingAction.get_video_action("zoom", meeting)
        self.assertIsInstance(action, ZoomGetVideo)
        self.assertEqual(action.mid, "zoom_mid")

    def test_invalid_platform_raises_runtime_error(self):
        """Test get_video_action raises RuntimeError for invalid platform."""
        meeting = {"mid": "test_mid"}
        with self.assertRaises(RuntimeError) as context:
            MeetingAction.get_video_action("invalid", meeting)
        self.assertIn("invalid platform type", str(context.exception))


class MeetingActionGetForceEndActionTest(TestCase):
    """Test MeetingAction.get_force_end_action for different platforms."""

    def test_tencent_force_end_action(self):
        """Test get_force_end_action returns TencentForceEndAction."""
        meeting = {"m_mid": "m_mid_123"}
        action = MeetingAction.get_force_end_action("tencent", meeting)
        self.assertIsInstance(action, TencentForceEndAction)
        self.assertEqual(action.m_mid, "m_mid_123")

    def test_wk_force_end_action(self):
        """Test get_force_end_action returns WkForceEndAction."""
        meeting = {"mid": "wk_mid"}
        action = MeetingAction.get_force_end_action("welink", meeting)
        self.assertIsInstance(action, WkForceEndAction)
        self.assertEqual(action.mid, "wk_mid")

    def test_zoom_force_end_action(self):
        """Test get_force_end_action returns ZoomForceEndAction."""
        meeting = {"mid": "zoom_mid"}
        action = MeetingAction.get_force_end_action("zoom", meeting)
        self.assertIsInstance(action, ZoomForceEndAction)
        self.assertEqual(action.mid, "zoom_mid")

    def test_invalid_platform_raises_runtime_error(self):
        """Test get_force_end_action raises RuntimeError for invalid platform."""
        meeting = {"mid": "test_mid"}
        with self.assertRaises(RuntimeError) as context:
            MeetingAction.get_force_end_action("invalid", meeting)
        self.assertIn("invalid platform type", str(context.exception))


class MeetingActionGetMeetingStatusActionTest(TestCase):
    """Test MeetingAction.get_meeting_status_action for different platforms."""

    def test_tencent_get_meeting_status_action(self):
        """Test get_meeting_status_action returns TencentGetMeetingStatusAction."""
        meeting = {"m_mid": "m_mid_123"}
        action = MeetingAction.get_meeting_status_action("tencent", meeting)
        self.assertIsInstance(action, TencentGetMeetingStatusAction)
        self.assertEqual(action.m_mid, "m_mid_123")

    def test_wk_get_meeting_status_action(self):
        """Test get_meeting_status_action returns WkGetMeetingStatusAction."""
        meeting = {"mid": "wk_mid"}
        action = MeetingAction.get_meeting_status_action("welink", meeting)
        self.assertIsInstance(action, WkGetMeetingStatusAction)
        self.assertEqual(action.mid, "wk_mid")

    def test_zoom_get_meeting_status_action(self):
        """Test get_meeting_status_action returns ZoomGetMeetingStatusAction."""
        meeting = {"mid": "zoom_mid"}
        action = MeetingAction.get_meeting_status_action("zoom", meeting)
        self.assertIsInstance(action, ZoomGetMeetingStatusAction)
        self.assertEqual(action.mid, "zoom_mid")

    def test_invalid_platform_raises_runtime_error(self):
        """Test get_meeting_status_action raises RuntimeError for invalid platform."""
        meeting = {"mid": "test_mid"}
        with self.assertRaises(RuntimeError) as context:
            MeetingAction.get_meeting_status_action("invalid", meeting)
        self.assertIn("invalid platform type", str(context.exception))


class MeetingAdapterImplCreateTest(TestCase):
    """Test MeetingAdapterImpl.create method."""

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.handler_meeting')
    def test_create_success(self, mock_handler):
        """Test create returns response when handler succeeds."""
        mock_handler.return_value = (200, {"mid": "new_mid", "host_id": "test@example.com"})

        adapter = MeetingAdapterImpl()
        meeting = {
            "community": "openEuler",
            "platform": "welink",
            "date": "2026-01-15",
            "start": "10:00",
            "end": "11:00",
            "topic": "Test Meeting",
            "is_private": False,
            "is_record": False,
            "is_cycle": False,
        }
        result = adapter.create("test@example.com", meeting)

        mock_handler.assert_called_once()
        self.assertEqual(result, {"mid": "new_mid", "host_id": "test@example.com"})

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.handler_meeting')
    def test_create_failure_raises_error(self, mock_handler):
        """Test create raises MyInnerError when handler fails."""
        mock_handler.return_value = (500, {"error": "Internal error"})

        adapter = MeetingAdapterImpl()
        meeting = {
            "community": "openEuler",
            "platform": "welink",
            "date": "2026-01-15",
            "start": "10:00",
            "end": "11:00",
            "topic": "Test Meeting",
            "is_private": False,
            "is_record": False,
            "is_cycle": False,
        }

        with self.assertRaises(MyInnerError):
            adapter.create("test@example.com", meeting)


class MeetingAdapterImplUpdateTest(TestCase):
    """Test MeetingAdapterImpl.update method."""

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.handler_meeting')
    def test_update_success(self, mock_handler):
        """Test update returns response when handler succeeds."""
        mock_handler.return_value = (200, {"mid": "updated_mid"})

        adapter = MeetingAdapterImpl()
        meeting = {
            "community": "openEuler",
            "platform": "welink",
            "host_id": "test@example.com",
            "mid": "wk_mid",
            "date": "2026-01-15",
            "start": "10:00",
            "end": "11:00",
            "topic": "Updated Meeting",
            "is_private": False,
            "is_record": False,
            "is_cycle": False,
        }
        result = adapter.update(meeting)

        mock_handler.assert_called_once()
        self.assertEqual(result, {"mid": "updated_mid"})

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.handler_meeting')
    def test_update_failure_raises_error(self, mock_handler):
        """Test update raises MyInnerError when handler fails."""
        mock_handler.return_value = (500, {"error": "Internal error"})

        adapter = MeetingAdapterImpl()
        meeting = {
            "community": "openEuler",
            "platform": "welink",
            "host_id": "test@example.com",
            "mid": "wk_mid",
            "date": "2026-01-15",
            "start": "10:00",
            "end": "11:00",
            "topic": "Test",
            "is_private": False,
            "is_record": False,
            "is_cycle": False,
        }

        with self.assertRaises(MyInnerError):
            adapter.update(meeting)


class MeetingAdapterImplUpdateSubTest(TestCase):
    """Test MeetingAdapterImpl.update_sub method."""

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.handler_meeting')
    def test_update_sub_success(self, mock_handler):
        """Test update_sub succeeds when handler returns 200."""
        # handler_meeting returns status directly for update_sub, not a tuple
        mock_handler.return_value = 200

        adapter = MeetingAdapterImpl()
        meeting = {
            "community": "openEuler",
            "platform": "welink",
            "host_id": "test@example.com",
            "mid": "wk_cycle_mid",
            "sub_id": "sub_001",
            "date": "2026-01-15",
            "start": "10:00",
            "end": "11:00",
        }
        adapter.update_sub(meeting)

        mock_handler.assert_called_once()

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.handler_meeting')
    def test_update_sub_failure_raises_error(self, mock_handler):
        """Test update_sub raises MyInnerError when handler fails."""
        mock_handler.return_value = 500

        adapter = MeetingAdapterImpl()
        meeting = {
            "community": "openEuler",
            "platform": "welink",
            "host_id": "test@example.com",
            "mid": "wk_cycle_mid",
            "sub_id": "sub_001",
            "date": "2026-01-15",
            "start": "10:00",
            "end": "11:00",
        }

        with self.assertRaises(MyInnerError):
            adapter.update_sub(meeting)


class MeetingAdapterImplDeleteTest(TestCase):
    """Test MeetingAdapterImpl.delete method."""

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.handler_meeting')
    def test_delete_success(self, mock_handler):
        """Test delete succeeds when handler returns 200."""
        mock_handler.return_value = 200

        adapter = MeetingAdapterImpl()
        meeting = {
            "community": "openEuler",
            "platform": "welink",
            "host_id": "test@example.com",
            "mid": "wk_mid",
            "is_cycle": False,
        }
        adapter.delete(meeting)

        mock_handler.assert_called_once()

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.handler_meeting')
    def test_delete_404_allowed(self, mock_handler):
        """Test delete does not raise error when handler returns 404."""
        mock_handler.return_value = 404

        adapter = MeetingAdapterImpl()
        meeting = {
            "community": "openEuler",
            "platform": "welink",
            "host_id": "test@example.com",
            "mid": "wk_mid",
            "is_cycle": False,
        }
        adapter.delete(meeting)  # Should not raise error

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.handler_meeting')
    def test_delete_failure_raises_error(self, mock_handler):
        """Test delete raises MyInnerError when handler returns other error."""
        mock_handler.return_value = 500

        adapter = MeetingAdapterImpl()
        meeting = {
            "community": "openEuler",
            "platform": "welink",
            "host_id": "test@example.com",
            "mid": "wk_mid",
            "is_cycle": False,
        }

        with self.assertRaises(MyInnerError):
            adapter.delete(meeting)


class MeetingAdapterImplDeleteSubTest(TestCase):
    """Test MeetingAdapterImpl.delete_sub method."""

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.handler_meeting')
    def test_delete_sub_success(self, mock_handler):
        """Test delete_sub succeeds when handler returns 200."""
        mock_handler.return_value = 200

        adapter = MeetingAdapterImpl()
        meeting = {
            "community": "openEuler",
            "platform": "welink",
            "host_id": "test@example.com",
            "mid": "wk_cycle_mid",
            "sub_id": "sub_001",
        }
        adapter.delete_sub(meeting)

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.handler_meeting')
    def test_delete_sub_404_allowed(self, mock_handler):
        """Test delete_sub does not raise error when handler returns 404."""
        mock_handler.return_value = 404

        adapter = MeetingAdapterImpl()
        meeting = {
            "community": "openEuler",
            "platform": "welink",
            "host_id": "test@example.com",
            "mid": "wk_cycle_mid",
            "sub_id": "sub_001",
        }
        adapter.delete_sub(meeting)  # Should not raise error

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.handler_meeting')
    def test_delete_sub_failure_raises_error(self, mock_handler):
        """Test delete_sub raises MyInnerError when handler returns other error."""
        mock_handler.return_value = 500

        adapter = MeetingAdapterImpl()
        meeting = {
            "community": "openEuler",
            "platform": "welink",
            "host_id": "test@example.com",
            "mid": "wk_cycle_mid",
            "sub_id": "sub_001",
        }

        with self.assertRaises(MyInnerError):
            adapter.delete_sub(meeting)


class MeetingAdapterImplGetParticipantsTest(TestCase):
    """Test MeetingAdapterImpl.get_participants method."""

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.handler_meeting')
    def test_get_participants_success(self, mock_handler):
        """Test get_participants returns data when handler succeeds."""
        mock_handler.return_value = (200, ["Alice", "Bob"])

        adapter = MeetingAdapterImpl()
        meeting = {
            "community": "openEuler",
            "platform": "welink",
            "host_id": "test@example.com",
            "mid": "wk_mid",
            "date": "2026-01-15",
            "start": "10:00",
            "end": "11:00",
        }
        result = adapter.get_participants(meeting)

        mock_handler.assert_called_once()
        self.assertEqual(result, ["Alice", "Bob"])

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.handler_meeting')
    def test_get_participants_failure_raises_error(self, mock_handler):
        """Test get_participants raises MyInnerError when handler fails."""
        mock_handler.return_value = (500, {"error": "Internal error"})

        adapter = MeetingAdapterImpl()
        meeting = {
            "community": "openEuler",
            "platform": "welink",
            "host_id": "test@example.com",
            "mid": "wk_mid",
            "date": "2026-01-15",
            "start": "10:00",
            "end": "11:00",
        }

        with self.assertRaises(MyInnerError):
            adapter.get_participants(meeting)


class MeetingAdapterImplGetVideoTest(TestCase):
    """Test MeetingAdapterImpl.get_video method."""

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.handler_meeting')
    def test_get_video_returns_handler_result(self, mock_handler):
        """Test get_video returns result from handler_meeting."""
        mock_handler.return_value = (200, {"video_url": "http://example.com/video.mp4"})

        adapter = MeetingAdapterImpl()
        meeting = {
            "community": "openEuler",
            "platform": "welink",
            "host_id": "test@example.com",
            "mid": "wk_mid",
            "date": "2026-01-15",
            "start": "10:00",
            "end": "11:00",
        }
        result = adapter.get_video(meeting)

        mock_handler.assert_called_once()
        self.assertEqual(result, (200, {"video_url": "http://example.com/video.mp4"}))


class MeetingAdapterImplForceEndTest(TestCase):
    """Test MeetingAdapterImpl.force_end_meeting method."""

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.handler_meeting')
    def test_force_end_returns_handler_result(self, mock_handler):
        """Test force_end_meeting returns result from handler_meeting."""
        mock_handler.return_value = (200, {"success": True})

        adapter = MeetingAdapterImpl()
        meeting = {
            "community": "openEuler",
            "platform": "welink",
            "host_id": "test@example.com",
            "mid": "wk_mid",
        }
        result = adapter.force_end_meeting(meeting)

        mock_handler.assert_called_once()
        self.assertEqual(result, (200, {"success": True}))


class MeetingAdapterImplGetMeetingStatusTest(TestCase):
    """Test MeetingAdapterImpl.get_meeting_status method."""

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.handler_meeting')
    def test_get_meeting_status_returns_handler_result(self, mock_handler):
        """Test get_meeting_status returns result from handler_meeting."""
        mock_handler.return_value = (200, {"status": "ongoing"})

        adapter = MeetingAdapterImpl()
        meeting = {
            "community": "openEuler",
            "platform": "welink",
            "host_id": "test@example.com",
            "mid": "wk_mid",
        }
        result = adapter.get_meeting_status(meeting)

        mock_handler.assert_called_once()
        self.assertEqual(result, (200, {"status": "ongoing"}))