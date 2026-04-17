#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
"""
Unit tests for force end meeting functionality.

Tests cover:
- ForceEndMeetingView.post endpoint (lines 310-320 in inner.py)
- MeetingApp.force_stop_meeting method (lines 585-617 in meeting.py)

Test cases:
- Force end non-cycle meeting success
- Force end cycle sub-meeting success
- Force end cycle meeting clears all ongoing sub-meetings
- Missing meeting_id returns 400
- Nonexistent meeting returns 400
- Nonexistent sub-meeting returns 400
"""
import datetime
import logging
from unittest import mock

from rest_framework import status

from meeting.infrastructure.dao.meeting_dao import MeetingDao
from meeting.infrastructure.dao.meeting_cycle_sub_dao import MeetingCycleSubMeetingDao
from meeting.domain.primitive.meeting_status import BusinessMeetingStatus
from meeting_platform.test.meeting.test_base import TestCommonMeeting

logger = logging.getLogger("log")


class ForceEndMeetingViewTest(TestCommonMeeting):
    """Test ForceEndMeetingView.post endpoint.

    Covers lines 310-320 in inner.py:
    - ForceEndMeetingView.post method
    - meeting_id validation
    - sub_id handling
    """

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
            "status": BusinessMeetingStatus.ONGOING.value,
        }
        defaults.update(kwargs)
        return MeetingDao.create(**defaults)

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
            "status": BusinessMeetingStatus.ONGOING.value,
            "warning_email_sent": False,
        }
        defaults.update(kwargs)
        return MeetingCycleSubMeetingDao.create(**defaults)

    @mock.patch("meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.force_end_meeting")
    def test_force_end_non_cycle_meeting_success(self, mock_force_end):
        """Test force end a non-cycle meeting successfully.

        Covers:
        - ForceEndMeetingView.post lines 314-320
        - MeetingApp.force_stop_meeting lines 605-616 for non-cycle meeting
        """
        mock_force_end.return_value = 200
        meeting = self._create_test_meeting(
            is_cycle=False,
            status=BusinessMeetingStatus.ONGOING.value
        )

        response = self.client.post(self.url, {"meeting_id": meeting.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify status was cleared to ENDED
        meeting.refresh_from_db()
        self.assertEqual(meeting.status, BusinessMeetingStatus.ENDED.value)
        self.assertFalse(meeting.warning_email_sent)

    @mock.patch("meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.force_end_meeting")
    def test_force_end_cycle_sub_meeting_success(self, mock_force_end):
        """Test force end a cycle sub-meeting successfully.

        Covers:
        - ForceEndMeetingView.post lines 314-320 with sub_id
        - MeetingApp.force_stop_meeting lines 593-603 for sub meeting
        """
        mock_force_end.return_value = 200

        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(
            parent,
            status=BusinessMeetingStatus.ONGOING.value,
            warning_email_sent=True
        )

        response = self.client.post(self.url, {
            "meeting_id": parent.id,
            "sub_id": sub.sub_id
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify sub meeting status was cleared
        sub.refresh_from_db()
        self.assertEqual(sub.status, BusinessMeetingStatus.ENDED.value)
        self.assertFalse(sub.warning_email_sent)

    @mock.patch("meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.force_end_meeting")
    def test_force_end_cycle_meeting_clears_all_ongoing_subs(self, mock_force_end):
        """Test force end cycle meeting clears all ongoing sub-meetings.

        Covers:
        - ForceEndMeetingView.post lines 314-320
        - MeetingApp.force_stop_meeting lines 608-613 for cycle meeting
        """
        mock_force_end.return_value = 200

        parent = self._create_parent_meeting()

        # Create multiple sub meetings with different statuses
        sub1 = self._create_sub_meeting(
            parent,
            status=BusinessMeetingStatus.ONGOING.value,
            sub_id=f"sub1_{datetime.datetime.now().timestamp()}"
        )
        sub2 = self._create_sub_meeting(
            parent,
            status=BusinessMeetingStatus.ONGOING.value,
            sub_id=f"sub2_{datetime.datetime.now().timestamp()}"
        )
        # Non-ongoing sub meeting should not be cleared
        sub3 = self._create_sub_meeting(
            parent,
            status=BusinessMeetingStatus.NOT_STARTED.value,
            sub_id=f"sub3_{datetime.datetime.now().timestamp()}"
        )

        response = self.client.post(self.url, {"meeting_id": parent.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify all ongoing sub meetings were cleared to ENDED
        sub1.refresh_from_db()
        sub2.refresh_from_db()
        sub3.refresh_from_db()
        self.assertEqual(sub1.status, BusinessMeetingStatus.ENDED.value)
        self.assertEqual(sub2.status, BusinessMeetingStatus.ENDED.value)
        # Non-ongoing sub meeting should remain unchanged
        self.assertEqual(sub3.status, BusinessMeetingStatus.NOT_STARTED.value)

    def test_force_end_missing_meeting_id(self):
        """Test missing meeting_id returns 400.

        Covers ForceEndMeetingView.post lines 315-317:
        - meeting_id validation check
        """
        response = self.client.post(self.url, {})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_force_end_nonexistent_meeting(self):
        """Test nonexistent meeting returns 400.

        Covers:
        - ForceEndMeetingView.post lines 314-320
        - MeetingApp.force_stop_meeting lines 587-589 for meeting not found
        """
        response = self.client.post(self.url, {"meeting_id": 99999})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_force_end_nonexistent_sub_meeting(self):
        """Test nonexistent sub-meeting returns 400.

        Covers:
        - ForceEndMeetingView.post lines 314-320 with invalid sub_id
        - MeetingApp.force_stop_meeting lines 594-597 for sub meeting not found
        """
        meeting = self._create_test_meeting(is_cycle=True)

        response = self.client.post(self.url, {
            "meeting_id": meeting.id,
            "sub_id": "nonexistent_sub_id"
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)