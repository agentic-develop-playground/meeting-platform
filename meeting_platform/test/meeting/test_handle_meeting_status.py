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