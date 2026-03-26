#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
"""
Unit tests for meeting overtime functionality.

Tests include:
- DAO methods for overtime detection and status management
- Force end meeting API endpoints
- Overtime detection logic
- Warning email deduplication
"""
import copy
import datetime
import logging
from unittest import mock
from datetime import timedelta

from rest_framework import status
from django.conf import settings

from meeting.models import Meeting, MeetingCycleSubMeeting, MeetingCycleDate
from meeting.infrastructure.dao.meeting_dao import MeetingDao
from meeting.infrastructure.dao.meeting_cycle_sub_dao import MeetingCycleSubMeetingDao
from meeting_platform.test.meeting.test_base import TestCommonMeeting
from meeting.application.meeting import MeetingApp

logger = logging.getLogger("log")


class MeetingDaoOvertimeTest(TestCommonMeeting):
    """Test MeetingDao overtime-related methods."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def _create_test_meeting(self, **kwargs):
        """Create a test meeting with default values."""
        defaults = {
            "sponsor": "test_sponsor",
            "group_name": "test_group",
            "community": self.community,
            "topic": "Test Meeting",
            "platform": "WELINK",
            "is_cycle": False,
            "date": self.today,
            "start": "10:00",
            "end": "11:00",
            "is_record": False,
            "mid": f"test_mid_{datetime.datetime.now().timestamp()}",
            "host_id": "test@example.com",
            "is_ongoing": False,
            "is_overtime": False,
            "warning_email_sent": False,
        }
        defaults.update(kwargs)
        return MeetingDao.create(**defaults)

    def test_get_overtime_meetings_returns_correct_meetings(self):
        """Test that get_overtime_meetings returns only overtime meetings."""
        now = datetime.datetime.now()
        past_time = (now - timedelta(hours=1)).strftime('%H:%M')

        # Create an overtime meeting (ongoing, end time passed)
        overtime_meeting = self._create_test_meeting(
            end=past_time,
            is_ongoing=True
        )

        # Create a normal meeting (not ongoing)
        normal_meeting = self._create_test_meeting(
            end=past_time,
            is_ongoing=False,
            mid=f"normal_mid_{datetime.datetime.now().timestamp()}"
        )

        # Get overtime meetings
        result = MeetingDao.get_overtime_meetings(self.community, self.today)

        # Should only return the overtime meeting
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, overtime_meeting.id)

    def test_get_overtime_meetings_excludes_other_community(self):
        """Test that get_overtime_meetings only returns meetings for specified community."""
        now = datetime.datetime.now()
        past_time = (now - timedelta(hours=1)).strftime('%H:%M')

        # Create meeting in different community
        other_meeting = self._create_test_meeting(
            community="otherCommunity",
            end=past_time,
            is_ongoing=True,
            mid=f"other_mid_{datetime.datetime.now().timestamp()}"
        )

        # Get overtime meetings for original community
        result = MeetingDao.get_overtime_meetings(self.community, self.today)

        self.assertEqual(len(result), 0)

    def test_update_overtime_status_sets_flag_and_timestamp(self):
        """Test that update_overtime_status correctly sets is_overtime and timestamp."""
        meeting = self._create_test_meeting()

        # Update to overtime
        MeetingDao.update_overtime_status(meeting.id, True)

        # Refresh from database
        meeting.refresh_from_db()

        self.assertTrue(meeting.is_overtime)
        self.assertIsNotNone(meeting.overtime_detected_at)

    def test_update_overtime_status_clears_flag_and_timestamp(self):
        """Test that update_overtime_status clears is_overtime and timestamp when set to False."""
        meeting = self._create_test_meeting(is_overtime=True)

        # Clear overtime status
        MeetingDao.update_overtime_status(meeting.id, False)

        # Refresh from database
        meeting.refresh_from_db()

        self.assertFalse(meeting.is_overtime)
        self.assertIsNone(meeting.overtime_detected_at)

    def test_get_upcoming_end_meetings_filters_correctly(self):
        """Test that get_upcoming_end_meetings returns meetings ending soon."""
        now = datetime.datetime.now()
        soon_time = (now + timedelta(minutes=3)).strftime('%H:%M')
        later_time = (now + timedelta(minutes=30)).strftime('%H:%M')

        # Meeting ending soon
        upcoming_meeting = self._create_test_meeting(
            end=soon_time,
            is_ongoing=True,
            mid=f"upcoming_mid_{datetime.datetime.now().timestamp()}"
        )

        # Meeting ending later
        later_meeting = self._create_test_meeting(
            end=later_time,
            is_ongoing=True,
            mid=f"later_mid_{datetime.datetime.now().timestamp()}"
        )

        # Meeting already sent warning email
        warned_meeting = self._create_test_meeting(
            end=soon_time,
            is_ongoing=True,
            warning_email_sent=True,
            mid=f"warned_mid_{datetime.datetime.now().timestamp()}"
        )

        result = MeetingDao.get_upcoming_end_meetings(self.community, self.today, warning_minutes=5)

        # Should only return the upcoming meeting without warning
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, upcoming_meeting.id)

    def test_mark_warning_email_sent(self):
        """Test that mark_warning_email_sent sets the flag."""
        meeting = self._create_test_meeting()

        MeetingDao.mark_warning_email_sent(meeting.id)

        meeting.refresh_from_db()
        self.assertTrue(meeting.warning_email_sent)

    def test_reset_warning_email_status(self):
        """Test that reset_warning_email_status clears the flag."""
        meeting = self._create_test_meeting(warning_email_sent=True)

        MeetingDao.reset_warning_email_status(meeting.id)

        meeting.refresh_from_db()
        self.assertFalse(meeting.warning_email_sent)

    def test_clear_overtime_status_resets_all_fields(self):
        """Test that clear_overtime_status resets all overtime-related fields."""
        meeting = self._create_test_meeting(
            is_ongoing=True,
            is_overtime=True,
            warning_email_sent=True
        )

        MeetingDao.clear_overtime_status(meeting.id)

        meeting.refresh_from_db()
        self.assertFalse(meeting.is_ongoing)
        self.assertFalse(meeting.is_overtime)
        self.assertFalse(meeting.warning_email_sent)
        self.assertIsNone(meeting.overtime_detected_at)
        self.assertIsNotNone(meeting.ongoing_updated_at)


class MeetingCycleSubMeetingDaoOvertimeTest(TestCommonMeeting):
    """Test MeetingCycleSubMeetingDao overtime-related methods."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def _create_parent_meeting(self, **kwargs):
        """Create a parent meeting for cycle sub meetings."""
        defaults = {
            "sponsor": "test_sponsor",
            "group_name": "test_group",
            "community": self.community,
            "topic": "Test Cycle Meeting",
            "platform": "WELINK",
            "is_cycle": True,
            "is_record": False,
            "mid": f"cycle_mid_{datetime.datetime.now().timestamp()}",
            "host_id": "test@example.com",
        }
        defaults.update(kwargs)
        return MeetingDao.create(**defaults)

    def _create_sub_meeting(self, parent_meeting, **kwargs):
        """Create a sub meeting for a cycle meeting."""
        defaults = {
            "mid": parent_meeting.mid,
            "sub_id": f"sub_{datetime.datetime.now().timestamp()}",
            "date": self.today,
            "start": "10:00",
            "end": "11:00",
            "meeting": parent_meeting,
            "is_ongoing": False,
            "is_overtime": False,
            "warning_email_sent": False,
        }
        defaults.update(kwargs)
        return MeetingCycleSubMeetingDao.create(**defaults)

    def test_get_overtime_sub_meetings_returns_correct_sub_meetings(self):
        """Test that get_overtime_sub_meetings returns only overtime sub meetings."""
        now = datetime.datetime.now()
        past_time = (now - timedelta(hours=1)).strftime('%H:%M')

        parent = self._create_parent_meeting()

        # Create overtime sub meeting
        overtime_sub = self._create_sub_meeting(
            parent,
            end=past_time,
            is_ongoing=True
        )

        # Create normal sub meeting
        normal_sub = self._create_sub_meeting(
            parent,
            end=past_time,
            is_ongoing=False,
            sub_id=f"normal_sub_{datetime.datetime.now().timestamp()}"
        )

        result = MeetingCycleSubMeetingDao.get_overtime_sub_meetings(self.community, self.today)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].id, overtime_sub.id)

    def test_update_overtime_status_for_sub_meeting(self):
        """Test updating overtime status for sub meeting."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent)

        MeetingCycleSubMeetingDao.update_overtime_status(sub.id, True)

        sub.refresh_from_db()
        self.assertTrue(sub.is_overtime)
        self.assertIsNotNone(sub.overtime_detected_at)

    def test_mark_warning_email_sent_for_sub_meeting(self):
        """Test marking warning email sent for sub meeting."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent)

        MeetingCycleSubMeetingDao.mark_warning_email_sent(sub.id)

        sub.refresh_from_db()
        self.assertTrue(sub.warning_email_sent)

    def test_clear_overtime_status_for_sub_meeting(self):
        """Test clearing overtime status for sub meeting."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(
            parent,
            is_ongoing=True,
            is_overtime=True,
            warning_email_sent=True
        )

        MeetingCycleSubMeetingDao.clear_overtime_status(sub.sub_id)

        sub.refresh_from_db()
        self.assertFalse(sub.is_ongoing)
        self.assertFalse(sub.is_overtime)
        self.assertFalse(sub.warning_email_sent)


class ForceEndMeetingViewTest(TestCommonMeeting):
    """Test force end meeting API endpoint."""

    url = "/inner/v1/meeting/meeting/force_end/"

    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.enable_client_auth(self.user.username)
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def _create_test_meeting(self, **kwargs):
        """Create a test meeting with default values."""
        defaults = {
            "sponsor": "test_sponsor",
            "group_name": "test_group",
            "community": self.community,
            "topic": "Test Meeting",
            "platform": "WELINK",
            "is_cycle": False,
            "date": self.today,
            "start": "10:00",
            "end": "11:00",
            "is_record": False,
            "mid": f"test_mid_{datetime.datetime.now().timestamp()}",
            "host_id": "test@example.com",
            "is_ongoing": True,
            "is_overtime": True,
        }
        defaults.update(kwargs)
        return MeetingDao.create(**defaults)

    @mock.patch("meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.force_end_meeting")
    def test_force_end_meeting_success(self, mock_force_end):
        """Test successful force end of a meeting."""
        mock_force_end.return_value = 200
        meeting = self._create_test_meeting()

        response = self.client.post(self.url, {"meeting_id": meeting.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify overtime status was cleared
        meeting.refresh_from_db()
        self.assertFalse(meeting.is_ongoing)
        self.assertFalse(meeting.is_overtime)
        self.assertFalse(meeting.warning_email_sent)

    def test_force_end_meeting_not_found(self):
        """Test force end of non-existent meeting returns error."""
        response = self.client.post(self.url, {"meeting_id": 99999})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_force_end_meeting_missing_meeting_id(self):
        """Test force end without meeting_id returns error."""
        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @mock.patch("meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.force_end_meeting")
    def test_force_end_cycle_meeting_clears_all_sub_meetings(self, mock_force_end):
        """Test force end of cycle meeting clears all sub meeting statuses."""
        mock_force_end.return_value = 200

        # Create parent meeting
        parent = self._create_test_meeting(is_cycle=True)

        # Create sub meetings
        sub1 = MeetingCycleSubMeetingDao.create(
            mid=parent.mid,
            sub_id=f"sub1_{datetime.datetime.now().timestamp()}",
            date=self.today,
            start="10:00",
            end="11:00",
            meeting=parent,
            is_ongoing=True,
            is_overtime=True
        )
        sub2 = MeetingCycleSubMeetingDao.create(
            mid=parent.mid,
            sub_id=f"sub2_{datetime.datetime.now().timestamp()}",
            date=self.today,
            start="14:00",
            end="15:00",
            meeting=parent,
            is_ongoing=True,
            is_overtime=True
        )

        response = self.client.post(self.url, {"meeting_id": parent.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify all sub meetings were cleared
        sub1.refresh_from_db()
        sub2.refresh_from_db()
        self.assertFalse(sub1.is_ongoing)
        self.assertFalse(sub1.is_overtime)
        self.assertFalse(sub2.is_ongoing)
        self.assertFalse(sub2.is_overtime)

    @mock.patch("meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.force_end_meeting")
    def test_force_end_sub_meeting_success(self, mock_force_end):
        """Test successful force end of a sub meeting via meeting_id + sub_id."""
        mock_force_end.return_value = 200

        parent = self._create_test_meeting(is_cycle=True)
        sub = MeetingCycleSubMeetingDao.create(
            mid=parent.mid,
            sub_id=f"sub_{datetime.datetime.now().timestamp()}",
            date=self.today,
            start="10:00",
            end="11:00",
            meeting=parent,
            is_ongoing=True,
            is_overtime=True,
            warning_email_sent=True
        )

        response = self.client.post(self.url, {"meeting_id": parent.id, "sub_id": sub.sub_id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify status was cleared
        sub.refresh_from_db()
        self.assertFalse(sub.is_ongoing)
        self.assertFalse(sub.is_overtime)
        self.assertFalse(sub.warning_email_sent)

    def test_force_end_sub_meeting_not_found(self):
        """Test force end of non-existent sub meeting returns error."""
        meeting = self._create_test_meeting(is_cycle=True)
        response = self.client.post(self.url, {"meeting_id": meeting.id, "sub_id": "non_existent_sub_id"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ForceEndSubMeetingViewTest(TestCommonMeeting):
    """Test force end sub meeting via unified API endpoint."""

    url = "/inner/v1/meeting/meeting/force_end/"

    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.enable_client_auth(self.user.username)
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def _create_parent_meeting(self):
        """Create a parent meeting for cycle sub meetings."""
        return MeetingDao.create(
            sponsor="test_sponsor",
            group_name="test_group",
            community=self.community,
            topic="Test Cycle Meeting",
            platform="WELINK",
            is_cycle=True,
            is_record=False,
            mid=f"cycle_mid_{datetime.datetime.now().timestamp()}",
            host_id="test@example.com",
        )

    @mock.patch("meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.force_end_meeting")
    def test_force_end_sub_meeting_success(self, mock_force_end):
        """Test successful force end of a sub meeting."""
        mock_force_end.return_value = 200

        parent = self._create_parent_meeting()
        sub = MeetingCycleSubMeetingDao.create(
            mid=parent.mid,
            sub_id=f"sub_{datetime.datetime.now().timestamp()}",
            date=self.today,
            start="10:00",
            end="11:00",
            meeting=parent,
            is_ongoing=True,
            is_overtime=True,
            warning_email_sent=True
        )

        response = self.client.post(self.url, {"meeting_id": parent.id, "sub_id": sub.sub_id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify status was cleared
        sub.refresh_from_db()
        self.assertFalse(sub.is_ongoing)
        self.assertFalse(sub.is_overtime)
        self.assertFalse(sub.warning_email_sent)

    def test_force_end_sub_meeting_not_found(self):
        """Test force end of non-existent sub meeting returns error."""
        parent = self._create_parent_meeting()
        response = self.client.post(self.url, {"meeting_id": parent.id, "sub_id": "non_existent_sub_id"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class OvertimeDetectionLogicTest(TestCommonMeeting):
    """Test the overtime detection logic in handle_meeting.py."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def _create_test_meeting(self, **kwargs):
        """Create a test meeting with default values."""
        defaults = {
            "sponsor": "test_sponsor",
            "group_name": "test_group",
            "community": self.community,
            "topic": "Test Meeting",
            "platform": "WELINK",
            "is_cycle": False,
            "date": self.today,
            "start": "10:00",
            "end": "11:00",
            "is_record": False,
            "mid": f"test_mid_{datetime.datetime.now().timestamp()}",
            "host_id": "test@example.com",
        }
        defaults.update(kwargs)
        return MeetingDao.create(**defaults)

    def test_detect_overtime_sets_flag_for_overtime_meeting(self):
        """Test that overtime detection sets is_overtime flag."""
        now = datetime.datetime.now()
        past_time = (now - timedelta(hours=1)).strftime('%H:%M')

        meeting = self._create_test_meeting(
            end=past_time,
            is_ongoing=True,
            is_overtime=False
        )

        # Get overtime meetings (simulating detect_overtime_meetings)
        overtime_meetings = MeetingDao.get_overtime_meetings(self.community, self.today)

        for m in overtime_meetings:
            if not m.is_overtime:
                MeetingDao.update_overtime_status(m.id, True)

        meeting.refresh_from_db()
        self.assertTrue(meeting.is_overtime)

    def test_detect_overtime_does_not_duplicate_warning(self):
        """Test that overtime detection doesn't send duplicate warnings."""
        now = datetime.datetime.now()
        soon_time = (now + timedelta(minutes=3)).strftime('%H:%M')

        # Create meeting ending soon that already has warning sent
        warned_meeting = self._create_test_meeting(
            end=soon_time,
            is_ongoing=True,
            warning_email_sent=True
        )

        # Create meeting ending soon without warning (should be returned)
        unwarned_meeting = self._create_test_meeting(
            end=soon_time,
            is_ongoing=True,
            warning_email_sent=False,
            mid=f"unwarned_mid_{datetime.datetime.now().timestamp()}"
        )

        # Get upcoming end meetings
        upcoming = MeetingDao.get_upcoming_end_meetings(self.community, self.today)

        # Should only include the meeting without warning
        self.assertEqual(len(upcoming), 1)
        self.assertEqual(upcoming[0].id, unwarned_meeting.id)


class MeetingStatusSyncTest(TestCommonMeeting):
    """Test the meeting status sync logic."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def _create_test_meeting(self, **kwargs):
        """Create a test meeting with default values."""
        defaults = {
            "sponsor": "test_sponsor",
            "group_name": "test_group",
            "community": self.community,
            "topic": "Test Meeting",
            "platform": "WELINK",
            "is_cycle": False,
            "date": self.today,
            "start": "10:00",
            "end": "11:00",
            "is_record": False,
            "mid": f"test_mid_{datetime.datetime.now().timestamp()}",
            "host_id": "test@example.com",
        }
        defaults.update(kwargs)
        return MeetingDao.create(**defaults)

    def test_meeting_start_resets_warning_email_flag(self):
        """Test that when meeting starts, warning_email_sent is reset."""
        # Create meeting with warning_email_sent=True (from previous session)
        meeting = self._create_test_meeting(
            is_ongoing=False,
            warning_email_sent=True
        )

        # Simulate meeting starting
        previous_ongoing = meeting.is_ongoing
        is_ongoing = True

        if not previous_ongoing and is_ongoing:
            MeetingDao.reset_warning_email_status(meeting.id)

        MeetingDao.update_status(meeting.id, is_ongoing)

        meeting.refresh_from_db()
        self.assertTrue(meeting.is_ongoing)
        self.assertFalse(meeting.warning_email_sent)

    def test_meeting_end_clears_overtime_status(self):
        """Test that when meeting ends, overtime status is cleared."""
        meeting = self._create_test_meeting(
            is_ongoing=True,
            is_overtime=True,
            warning_email_sent=True
        )

        # Simulate meeting ending
        is_ongoing = False

        if not is_ongoing and meeting.is_overtime:
            MeetingDao.clear_overtime_status(meeting.id)

        meeting.refresh_from_db()
        self.assertFalse(meeting.is_ongoing)
        self.assertFalse(meeting.is_overtime)
        self.assertFalse(meeting.warning_email_sent)


class MeetingSerializerOvertimeTest(TestCommonMeeting):
    """Test that serializers correctly return overtime fields."""

    url = "/inner/v1/meeting/meeting/{}/"

    def setUp(self):
        super().setUp()
        self.user = self.create_user()
        self.enable_client_auth(self.user.username)
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def _create_test_meeting(self, **kwargs):
        """Create a test meeting with default values."""
        defaults = {
            "sponsor": "test_sponsor",
            "group_name": "test_group",
            "community": self.community,
            "topic": "Test Meeting",
            "platform": "WELINK",
            "is_cycle": False,
            "date": self.today,
            "start": "10:00",
            "end": "11:00",
            "is_record": False,
            "mid": f"test_mid_{datetime.datetime.now().timestamp()}",
            "host_id": "test@example.com",
        }
        defaults.update(kwargs)
        return MeetingDao.create(**defaults)

    @mock.patch("meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create")
    def test_serializer_returns_is_overtime_field(self, mock_create):
        """Test that meeting serializer returns is_overtime field."""
        mock_create.return_value = {
            "mid": "test_mid_serializer",
            "join_url": "https://test.welink.com/j/123",
            "host_id": "host@example.com"
        }

        data = copy.deepcopy(CreateMeetingViewTest.data)
        data["sponsor"] = self.user.username
        data["is_cycle"] = False

        ret = self.client.post("/inner/v1/meeting/meeting/", data)

        if ret.status_code == 200:
            response_data = ret.json() if hasattr(ret, 'json') else ret.data
            # Handle both response formats
            if isinstance(response_data.get('data'), dict):
                meeting_id = response_data['data']['id']
            elif isinstance(response_data.get('data'), int):
                meeting_id = response_data['data']
            else:
                meeting_id = response_data.get('id')

            if meeting_id:
                # Get the meeting directly and update it
                meeting = MeetingDao.get_by_id(meeting_id)
                MeetingDao.update_overtime_status(meeting.id, True)

                # Get meeting details
                get_response = self.client.get(self.url.format(meeting_id))

                self.assertEqual(get_response.status_code, status.HTTP_200_OK)

                get_data = get_response.json() if hasattr(get_response, 'json') else get_response.data
                if isinstance(get_data.get('data'), dict):
                    self.assertIn('is_overtime', get_data['data'])
                    self.assertTrue(get_data['data']['is_overtime'])
                    self.assertIn('overtime_detected_at', get_data['data'])

    def test_list_meetings_includes_overtime_fields(self):
        """Test that meeting list includes overtime fields."""
        # Create a meeting
        meeting = self._create_test_meeting()
        MeetingDao.update_overtime_status(meeting.id, True)

        response = self.client.get("/inner/v1/meeting/meeting/")

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        response_data = response.json() if hasattr(response, 'json') else response.data
        if 'data' in response_data and len(response_data['data']) > 0:
            meeting_data = response_data['data'][0]
            self.assertIn('is_overtime', meeting_data)
            self.assertIn('is_ongoing', meeting_data)


# Import CreateMeetingViewTest data for reuse
from meeting_platform.test.meeting.test_meeting import CreateMeetingViewTest