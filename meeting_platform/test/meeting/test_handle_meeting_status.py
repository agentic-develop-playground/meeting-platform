#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
"""
Unit tests for handle_meeting_status.py static methods.

Tests include:
- _calculate_status() - business status calculation logic
- _should_send_warning() - warning email timing logic
"""
import datetime
from unittest import mock

from django.conf import settings

from meeting.management.commands.handle_meeting_status import HandleMeetingStatus
from meeting.domain.primitive.meeting_status import BusinessMeetingStatus
from meeting_platform.test.meeting.test_base import TestCommonMeeting


class CalculateStatusStaticMethodTest(TestCommonMeeting):
    """Test the _calculate_status static method."""

    def setUp(self):
        super().setUp()
        self.today = "2026-04-14"

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def test_calculate_status_not_started_before_meeting(self):
        """Test status NOT_STARTED when current time < meeting start time."""
        # Meeting starts at 14:00, current time is 10:00
        now = datetime.datetime.strptime(f"{self.today} 10:00", "%Y-%m-%d %H:%M")
        result = HandleMeetingStatus._calculate_status(
            date=self.today,
            start="14:00",
            end="15:00",
            api_status=False,  # No ongoing meeting from API
            now=now
        )
        self.assertEqual(result, BusinessMeetingStatus.NOT_STARTED.value)

    def test_calculate_status_ongoing_during_meeting(self):
        """Test status ONGOING when current time is within meeting time range."""
        # Meeting is 10:00-11:00, current time is 10:30
        now = datetime.datetime.strptime(f"{self.today} 10:30", "%Y-%m-%d %H:%M")
        result = HandleMeetingStatus._calculate_status(
            date=self.today,
            start="10:00",
            end="11:00",
            api_status=False,
            now=now
        )
        self.assertEqual(result, BusinessMeetingStatus.ONGOING.value)

    def test_calculate_status_ongoing_with_api_status(self):
        """Test status ONGOING when API returns meeting is ongoing."""
        # Meeting is 10:00-11:00, current time is 10:30, API says ongoing
        now = datetime.datetime.strptime(f"{self.today} 10:30", "%Y-%m-%d %H:%M")
        result = HandleMeetingStatus._calculate_status(
            date=self.today,
            start="10:00",
            end="11:00",
            api_status=True,  # Meeting is ongoing per API
            now=now
        )
        self.assertEqual(result, BusinessMeetingStatus.ONGOING.value)

    def test_calculate_status_ended_after_meeting(self):
        """Test status ENDED when current time > end time and API not ongoing."""
        # Meeting ended at 10:00, current time is 11:00, API says not ongoing
        now = datetime.datetime.strptime(f"{self.today} 11:00", "%Y-%m-%d %H:%M")
        result = HandleMeetingStatus._calculate_status(
            date=self.today,
            start="09:00",
            end="10:00",
            api_status=False,
            now=now
        )
        self.assertEqual(result, BusinessMeetingStatus.ENDED.value)

    def test_calculate_status_overtime_with_api_status(self):
        """Test status OVERTIME when time > end but API says ongoing."""
        # Meeting should end at 10:00, current time is 11:00, API says still ongoing
        now = datetime.datetime.strptime(f"{self.today} 11:00", "%Y-%m-%d %H:%M")
        result = HandleMeetingStatus._calculate_status(
            date=self.today,
            start="09:00",
            end="10:00",
            api_status=True,  # Meeting still ongoing per API (overtime)
            now=now
        )
        self.assertEqual(result, BusinessMeetingStatus.OVERTIME.value)

    def test_calculate_status_overtime_at_exact_end_time(self):
        """Test status OVERTIME when exactly at end time with API ongoing."""
        # At exactly 10:00 (end time), API says ongoing
        now = datetime.datetime.strptime(f"{self.today} 10:00", "%Y-%m-%d %H:%M")
        result = HandleMeetingStatus._calculate_status(
            date=self.today,
            start="09:00",
            end="10:00",
            api_status=True,
            now=now
        )
        # At exact end time, now > meeting_end_time is False (not strictly greater)
        # So it should return ONGOING, not OVERTIME
        self.assertEqual(result, BusinessMeetingStatus.ONGOING.value)

    def test_calculate_status_overtime_one_minute_after(self):
        """Test status OVERTIME one minute after end time with API ongoing."""
        # One minute after end time
        now = datetime.datetime.strptime(f"{self.today} 10:01", "%Y-%m-%d %H:%M")
        result = HandleMeetingStatus._calculate_status(
            date=self.today,
            start="09:00",
            end="10:00",
            api_status=True,
            now=now
        )
        self.assertEqual(result, BusinessMeetingStatus.OVERTIME.value)

    def test_calculate_status_missing_date(self):
        """Test status NOT_STARTED when date is None."""
        now = datetime.datetime.now()
        result = HandleMeetingStatus._calculate_status(
            date=None,
            start="10:00",
            end="11:00",
            api_status=False,
            now=now
        )
        self.assertEqual(result, BusinessMeetingStatus.NOT_STARTED.value)

    def test_calculate_status_missing_start_time(self):
        """Test status NOT_STARTED when start time is None."""
        now = datetime.datetime.now()
        result = HandleMeetingStatus._calculate_status(
            date=self.today,
            start=None,
            end="11:00",
            api_status=False,
            now=now
        )
        self.assertEqual(result, BusinessMeetingStatus.NOT_STARTED.value)

    def test_calculate_status_missing_end_time(self):
        """Test status NOT_STARTED when end time is None."""
        now = datetime.datetime.now()
        result = HandleMeetingStatus._calculate_status(
            date=self.today,
            start="10:00",
            end=None,
            api_status=False,
            now=now
        )
        self.assertEqual(result, BusinessMeetingStatus.NOT_STARTED.value)

    def test_calculate_status_invalid_date_format(self):
        """Test status NOT_STARTED when date format is invalid."""
        now = datetime.datetime.now()
        result = HandleMeetingStatus._calculate_status(
            date="invalid-date",
            start="10:00",
            end="11:00",
            api_status=False,
            now=now
        )
        self.assertEqual(result, BusinessMeetingStatus.NOT_STARTED.value)

    def test_calculate_status_invalid_time_format(self):
        """Test status NOT_STARTED when time format is invalid."""
        now = datetime.datetime.now()
        result = HandleMeetingStatus._calculate_status(
            date=self.today,
            start="invalid-time",
            end="11:00",
            api_status=False,
            now=now
        )
        self.assertEqual(result, BusinessMeetingStatus.NOT_STARTED.value)

    def test_calculate_status_boundary_at_start_time(self):
        """Test status ONGOING when exactly at start time."""
        now = datetime.datetime.strptime(f"{self.today} 10:00", "%Y-%m-%d %H:%M")
        result = HandleMeetingStatus._calculate_status(
            date=self.today,
            start="10:00",
            end="11:00",
            api_status=False,
            now=now
        )
        # At exact start time: meeting_start_time <= now is True
        self.assertEqual(result, BusinessMeetingStatus.ONGOING.value)

    def test_calculate_status_boundary_at_end_time_no_api(self):
        """Test status ENDED when exactly at end time without API status."""
        now = datetime.datetime.strptime(f"{self.today} 11:00", "%Y-%m-%d %H:%M")
        result = HandleMeetingStatus._calculate_status(
            date=self.today,
            start="10:00",
            end="11:00",
            api_status=False,
            now=now
        )
        # At exact end time: now <= meeting_end_time is True, so ONGOING
        self.assertEqual(result, BusinessMeetingStatus.ONGOING.value)

    def test_calculate_status_one_second_before_start(self):
        """Test status NOT_STARTED one second before start."""
        now = datetime.datetime.strptime(f"{self.today} 09:59:59", "%Y-%m-%d %H:%M:%S")
        result = HandleMeetingStatus._calculate_status(
            date=self.today,
            start="10:00",
            end="11:00",
            api_status=False,
            now=now
        )
        self.assertEqual(result, BusinessMeetingStatus.NOT_STARTED.value)

    def test_calculate_status_one_second_after_end(self):
        """Test status ENDED one second after end without API."""
        now = datetime.datetime.strptime(f"{self.today} 11:00:01", "%Y-%m-%d %H:%M:%S")
        result = HandleMeetingStatus._calculate_status(
            date=self.today,
            start="10:00",
            end="11:00",
            api_status=False,
            now=now
        )
        self.assertEqual(result, BusinessMeetingStatus.ENDED.value)


class ShouldSendWarningStaticMethodTest(TestCommonMeeting):
    """Test the _should_send_warning static method."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = "2026-04-14"

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def test_should_send_warning_at_exact_warning_time(self):
        """Test should send warning exactly at warning time (30 min before next meeting)."""
        # Next meeting starts at 14:00, warning time is 13:30
        now = datetime.datetime.strptime(f"{self.today} 13:30", "%Y-%m-%d %H:%M")
        result = HandleMeetingStatus._should_send_warning("14:00", now)
        self.assertTrue(result)

    def test_should_send_warning_within_tolerance_before(self):
        """Test should send warning 30 seconds before warning time."""
        # Warning time is 13:30, current time is 13:29:30 (30 seconds before)
        now = datetime.datetime.strptime(f"{self.today} 13:29:30", "%Y-%m-%d %H:%M:%S")
        result = HandleMeetingStatus._should_send_warning("14:00", now)
        self.assertTrue(result)

    def test_should_send_warning_within_tolerance_after(self):
        """Test should send warning 30 seconds after warning time."""
        # Warning time is 13:30, current time is 13:30:30 (30 seconds after)
        now = datetime.datetime.strptime(f"{self.today} 13:30:30", "%Y-%m-%d %H:%M:%S")
        result = HandleMeetingStatus._should_send_warning("14:00", now)
        self.assertTrue(result)

    def test_should_not_send_warning_outside_tolerance_before(self):
        """Test should NOT send warning 61 seconds before warning time."""
        # Warning time is 13:30, current time is 13:28:59 (61 seconds before)
        now = datetime.datetime.strptime(f"{self.today} 13:28:59", "%Y-%m-%d %H:%M:%S")
        result = HandleMeetingStatus._should_send_warning("14:00", now)
        self.assertFalse(result)

    def test_should_not_send_warning_outside_tolerance_after(self):
        """Test should NOT send warning 61 seconds after warning time."""
        # Warning time is 13:30, current time is 13:31:01 (61 seconds after)
        now = datetime.datetime.strptime(f"{self.today} 13:31:01", "%Y-%m-%d %H:%M:%S")
        result = HandleMeetingStatus._should_send_warning("14:00", now)
        self.assertFalse(result)

    def test_should_not_send_warning_early(self):
        """Test should NOT send warning when too early."""
        # Next meeting at 14:00, current time is 10:00 (4 hours before warning time)
        now = datetime.datetime.strptime(f"{self.today} 10:00", "%Y-%m-%d %H:%M")
        result = HandleMeetingStatus._should_send_warning("14:00", now)
        self.assertFalse(result)

    def test_should_not_send_warning_late(self):
        """Test should NOT send warning when past warning window."""
        # Next meeting at 14:00, current time is 14:00 (meeting already started)
        now = datetime.datetime.strptime(f"{self.today} 14:00", "%Y-%m-%d %H:%M")
        result = HandleMeetingStatus._should_send_warning("14:00", now)
        self.assertFalse(result)

    def test_should_send_warning_different_warning_advance_time(self):
        """Test warning timing with different OVER_TIME_WARNING_ADVANCE_TIME."""
        # Default is 30 minutes, but we mock settings to use 15 minutes
        with mock.patch.object(settings, 'OVER_TIME_WARNING_ADVANCE_TIME', 15):
            # Next meeting at 14:00, warning time would be 13:45 (15 min before)
            now = datetime.datetime.strptime(f"{self.today} 13:45", "%Y-%m-%d %H:%M")
            result = HandleMeetingStatus._should_send_warning("14:00", now)
            self.assertTrue(result)

            # At 13:30 (original 30 min warning time), should NOT send
            now = datetime.datetime.strptime(f"{self.today} 13:30", "%Y-%m-%d %H:%M")
            result = HandleMeetingStatus._should_send_warning("14:00", now)
            self.assertFalse(result)

    def test_should_send_warning_invalid_time_format(self):
        """Test returns False for invalid time format."""
        now = datetime.datetime.now()
        result = HandleMeetingStatus._should_send_warning("invalid-time", now)
        self.assertFalse(result)

    def test_should_send_warning_empty_time_string(self):
        """Test returns False for empty time string."""
        now = datetime.datetime.now()
        result = HandleMeetingStatus._should_send_warning("", now)
        self.assertFalse(result)

    def test_should_send_warning_malformed_time(self):
        """Test returns False for malformed time string."""
        now = datetime.datetime.now()
        # Missing minutes
        result = HandleMeetingStatus._should_send_warning("14", now)
        self.assertFalse(result)

    def test_should_send_warning_edge_case_next_meeting_early(self):
        """Test warning for next meeting early in the day."""
        # Next meeting at 08:00, warning time is 07:30
        now = datetime.datetime.strptime(f"{self.today} 07:30", "%Y-%m-%d %H:%M")
        result = HandleMeetingStatus._should_send_warning("08:00", now)
        self.assertTrue(result)

    def test_should_send_warning_edge_case_next_meeting_late(self):
        """Test warning for next meeting late in the day."""
        # Next meeting at 23:00, warning time is 22:30
        now = datetime.datetime.strptime(f"{self.today} 22:30", "%Y-%m-%d %H:%M")
        result = HandleMeetingStatus._should_send_warning("23:00", now)
        self.assertTrue(result)


class SyncSubMeetingTest(TestCommonMeeting):
    """Test the _sync_sub_meeting method."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = "2026-04-14"
        self.handler = HandleMeetingStatus(self.community)

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def _create_parent_meeting(self, **kwargs):
        """Create a parent meeting for cycle sub meetings."""
        from meeting.infrastructure.dao.meeting_dao import MeetingDao
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
        from meeting.infrastructure.dao.meeting_cycle_sub_dao import MeetingCycleSubMeetingDao
        defaults = {
            "mid": parent_meeting.mid,
            "sub_id": f"sub_{datetime.datetime.now().timestamp()}",
            "date": self.today,
            "start": "10:00",
            "end": "11:00",
            "meeting": parent_meeting,
            "status": BusinessMeetingStatus.NOT_STARTED.value,
            "warning_email_sent": False,
        }
        defaults.update(kwargs)
        return MeetingCycleSubMeetingDao.create(**defaults)

    @mock.patch.object(HandleMeetingStatus, 'meeting_adapter_impl')
    def test_sync_sub_meeting_status_update(self, mock_adapter):
        """Test sub-meeting status synchronization."""

        # Setup: meeting is within time range but API says not ongoing
        mock_adapter.get_meeting_status.return_value = False

        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(
            parent_meeting=parent,
            status=BusinessMeetingStatus.NOT_STARTED.value
        )

        # Current time is during meeting (10:30)
        now = datetime.datetime.strptime(f"{self.today} 10:30", "%Y-%m-%d %H:%M")
        meeting_dict = {"sub_id": sub.sub_id, "platform": parent.platform, "mid": parent.mid}

        # Execute sync
        self.handler._sync_sub_meeting(parent, sub, meeting_dict, now)

        # Verify status updated to ONGOING
        sub.refresh_from_db()
        self.assertEqual(sub.status, BusinessMeetingStatus.ONGOING.value)

        # Verify DAO update_status was called
        self.assertIsNotNone(sub.status_updated_at)

    @mock.patch.object(HandleMeetingStatus, 'meeting_adapter_impl')
    def test_sync_sub_meeting_overtime_detection(self, mock_adapter):
        """Test overtime detection for sub-meetings."""

        # Setup: meeting ended but API says still ongoing (overtime)
        mock_adapter.get_meeting_status.return_value = True

        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(
            parent_meeting=parent,
            start="09:00",
            end="10:00",
            status=BusinessMeetingStatus.ONGOING.value
        )

        # Current time is after meeting end (11:00)
        now = datetime.datetime.strptime(f"{self.today} 11:00", "%Y-%m-%d %H:%M")
        meeting_dict = {"sub_id": sub.sub_id, "platform": parent.platform, "mid": parent.mid}

        # Execute sync
        self.handler._sync_sub_meeting(parent, sub, meeting_dict, now)

        # Verify status updated to OVERTIME
        sub.refresh_from_db()
        self.assertEqual(sub.status, BusinessMeetingStatus.OVERTIME.value)

    @mock.patch.object(HandleMeetingStatus, 'meeting_adapter_impl')
    def test_sync_sub_meeting_reset_warning_email_on_start(self, mock_adapter):
        """Test reset warning email status when meeting starts."""

        # Setup: meeting transitioning from NOT_STARTED to ONGOING
        mock_adapter.get_meeting_status.return_value = False

        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(
            parent_meeting=parent,
            status=BusinessMeetingStatus.NOT_STARTED.value,
            warning_email_sent=True  # Was previously sent warning
        )

        # Current time is during meeting (10:30)
        now = datetime.datetime.strptime(f"{self.today} 10:30", "%Y-%m-%d %H:%M")
        meeting_dict = {"sub_id": sub.sub_id, "platform": parent.platform, "mid": parent.mid}

        # Execute sync
        self.handler._sync_sub_meeting(parent, sub, meeting_dict, now)

        # Verify warning_email_sent was reset to False
        sub.refresh_from_db()
        self.assertEqual(sub.status, BusinessMeetingStatus.ONGOING.value)
        self.assertFalse(sub.warning_email_sent)


class SendWarningEmailTest(TestCommonMeeting):
    """Test the send_warning_emails and _send_warning_email methods."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = "2026-04-14"
        self.handler = HandleMeetingStatus(self.community)

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def _create_test_meeting(self, **kwargs):
        """Create a test meeting with default values."""
        from meeting.infrastructure.dao.meeting_dao import MeetingDao
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
            "warning_email_sent": False,
        }
        defaults.update(kwargs)
        return MeetingDao.create(**defaults)

    def _create_parent_meeting(self, **kwargs):
        """Create a parent meeting for cycle sub meetings."""
        from meeting.infrastructure.dao.meeting_dao import MeetingDao
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
        from meeting.infrastructure.dao.meeting_cycle_sub_dao import MeetingCycleSubMeetingDao
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

    @mock.patch('meeting.management.commands.handle_meeting_status.EmailAdapter')
    @mock.patch.object(HandleMeetingStatus, '_get_next_meeting_start_time')
    @mock.patch('django.conf.settings.OPERATOR_EMAILS')
    def test_send_warning_email_success(self, mock_operator_emails, mock_get_next, mock_email_adapter_class):
        """Test warning email sent successfully."""

        # Setup operator emails
        mock_operator_emails.__getitem__ = lambda self, key: ['operator@example.com']
        mock_operator_emails.get = lambda key, default=None: ['operator@example.com']

        # Setup: next meeting starts at 14:00, current time is 13:30 (warning time)
        mock_get_next.return_value = "14:00"

        # Setup mock EmailAdapter instance
        mock_email_adapter_instance = mock.MagicMock()
        mock_email_adapter_instance.send_message.return_value = None
        mock_email_adapter_class.return_value = mock_email_adapter_instance

        meeting = self._create_test_meeting(
            end="11:00",
            host_id="test@example.com"
        )

        # Create next meeting for the same host
        next_meeting = self._create_test_meeting(
            start="14:00",
            end="15:00",
            host_id="test@example.com",
            mid=f"next_mid_{datetime.datetime.now().timestamp()}"
        )

        # Mock time to be at warning time (30 min before next meeting)
        now = datetime.datetime.strptime(f"{self.today} 13:30", "%Y-%m-%d %H:%M")

        # Execute with mocked time
        with mock.patch('datetime.datetime', wraps=datetime.datetime) as mock_datetime:
            mock_datetime.now.return_value = now

            # Call _send_warning_email directly
            self.handler._send_warning_email(meeting, ['operator@example.com'])

        # Verify email was sent
        mock_email_adapter_instance.send_message.assert_called_once()

        # Verify warning_email_sent was marked
        meeting.refresh_from_db()
        self.assertTrue(meeting.warning_email_sent)

    @mock.patch('meeting.management.commands.handle_meeting_status.EmailAdapter')
    @mock.patch.object(HandleMeetingStatus, '_get_next_meeting_start_time')
    @mock.patch('django.conf.settings.OPERATOR_EMAILS')
    def test_send_warning_email_for_sub_meeting(self, mock_operator_emails, mock_get_next, mock_email_adapter_class):
        """Test warning email for sub-meeting."""

        # Setup operator emails
        mock_operator_emails.__getitem__ = lambda self, key: ['operator@example.com']
        mock_operator_emails.get = lambda key, default=None: ['operator@example.com']

        # Setup: next meeting starts at 14:00
        mock_get_next.return_value = "14:00"

        # Setup mock EmailAdapter instance
        mock_email_adapter_instance = mock.MagicMock()
        mock_email_adapter_instance.send_message.return_value = None
        mock_email_adapter_class.return_value = mock_email_adapter_instance

        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(
            parent_meeting=parent,
            end="11:00",
            status=BusinessMeetingStatus.ONGOING.value
        )

        # Mock time to be at warning time
        now = datetime.datetime.strptime(f"{self.today} 13:30", "%Y-%m-%d %H:%M")

        # Execute with mocked time
        with mock.patch('datetime.datetime', wraps=datetime.datetime) as mock_datetime:
            mock_datetime.now.return_value = now

            # Call _send_warning_email with sub_meeting
            self.handler._send_warning_email(parent, ['operator@example.com'], sub_meeting=sub)

        # Verify email was sent
        mock_email_adapter_instance.send_message.assert_called_once()

        # Verify warning_email_sent was marked for sub meeting
        sub.refresh_from_db()
        self.assertTrue(sub.warning_email_sent)

    @mock.patch('meeting.management.commands.handle_meeting_status.EmailAdapter')
    @mock.patch.object(HandleMeetingStatus, '_get_next_meeting_start_time')
    @mock.patch('django.conf.settings.OPERATOR_EMAILS')
    def test_send_warning_email_exception_handling(self, mock_operator_emails, mock_get_next, mock_email_adapter_class):
        """Test exception handling during email send."""

        # Setup operator emails
        mock_operator_emails.__getitem__ = lambda self, key: ['operator@example.com']
        mock_operator_emails.get = lambda key, default=None: ['operator@example.com']

        # Setup next meeting time
        mock_get_next.return_value = "14:00"

        # Setup: EmailAdapter send_message raises exception
        mock_email_adapter_instance = mock.MagicMock()
        mock_email_adapter_instance.send_message.side_effect = Exception("SMTP error")
        mock_email_adapter_class.return_value = mock_email_adapter_instance

        meeting = self._create_test_meeting(
            end="11:00",
            host_id="test@example.com"
        )

        # Mock time
        now = datetime.datetime.strptime(f"{self.today} 13:30", "%Y-%m-%d %H:%M")

        # Execute - should not raise exception
        with mock.patch('datetime.datetime', wraps=datetime.datetime) as mock_datetime:
            mock_datetime.now.return_value = now

            # Call _send_warning_email - should handle exception gracefully
            self.handler._send_warning_email(meeting, ['operator@example.com'])

        # Verify warning_email_sent was NOT marked due to error
        meeting.refresh_from_db()
        self.assertFalse(meeting.warning_email_sent)

    @mock.patch.object(HandleMeetingStatus, '_get_next_meeting_start_time')
    def test_send_warning_emails_no_operator_emails(self, mock_get_next):
        """Test no operator emails configured."""

        # Create an ongoing meeting
        meeting = self._create_test_meeting()

        # Mock settings to return no operator emails
        with mock.patch('django.conf.settings.OPERATOR_EMAILS', {}) as mock_emails:
            # Execute send_warning_emails
            self.handler.send_warning_emails()

        # Verify _get_next_meeting_start_time was never called (early return)
        mock_get_next.assert_not_called()

        # Verify warning_email_sent was not marked
        meeting.refresh_from_db()
        self.assertFalse(meeting.warning_email_sent)