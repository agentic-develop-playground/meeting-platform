#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
import logging
import uuid
import base64
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from rest_framework.test import APITestCase
from rest_framework import status

from meeting.models import (
    Meeting, User, MeetingCycleDate, MeetingCycleSubMeeting,
    MeetingBiliRecords, MeetingObsRecords
)

logger = logging.getLogger("log")


class CommonClass:
    """Base class with common database operations for all meeting tests."""

    meeting_dao = Meeting
    user_dao = User

    def create_user(self):
        """Create a test user with unique username."""
        uuid_str = str(uuid.uuid4())
        new_uuid_str = uuid_str.replace("-", "")
        username = "test_{}".format(new_uuid_str)
        user = self.user_dao.objects.create_superuser(username, None, username)
        return user

    def get_all_user(self):
        """Get all users."""
        return self.user_dao.objects.all()

    def get_user_by_id(self, user_id):
        """Get user by ID."""
        return self.user_dao.objects.filter(id=user_id).first()

    def get_users_by_username(self, username):
        """Get user by username."""
        return self.user_dao.objects.filter(sponsor=username).first()

    def clear_user(self):
        """Delete all meetings (legacy method - should delete users instead)."""
        ret = self.meeting_dao.objects.all().delete()
        logger.info("delete user and result is:{}".format(str(ret)))

    def clear_all_users(self):
        """Delete all users from database."""
        ret = self.user_dao.objects.all().delete()
        logger.info("delete all users and result is:{}".format(str(ret)))

    def create_meeting(self, **kwargs):
        """Create a meeting directly in database."""
        return self.meeting_dao.objects.create(**kwargs)

    def get_meeting_by_username(self, username):
        """Get first meeting by sponsor username."""
        return self.meeting_dao.objects.filter(sponsor=username).first()

    def get_meeting_by_mid(self, mid):
        """Get meeting by meeting ID."""
        return self.meeting_dao.objects.filter(mid=mid).first()

    def get_meetings(self):
        """Get all meetings."""
        return self.meeting_dao.objects.all()

    def get_meetings_by_username(self, username):
        """Get all meetings by sponsor username."""
        return self.meeting_dao.objects.filter(sponsor=username).all()

    def clear_meetings(self):
        """Delete all meetings from database."""
        ret = self.meeting_dao.objects.all().delete()
        logger.info("delete meeting and result is:{}".format(str(ret)))

    def format_token(self, token):
        """Format basic auth token."""
        return "basic {}".format(str(token))

    # noinspection PyUnresolvedReferences
    def enable_client_auth(self, username):
        """Enable basic authentication for test client."""
        data = "{}:{}".format(username, username)
        base64_str = base64.b64encode(data.encode()).decode("utf-8")
        self.client.credentials(HTTP_AUTHORIZATION=self.format_token(base64_str))


class TestCommonMeeting(CommonClass, APITestCase):
    """
    Base test class for all meeting tests.

    Provides standard setup/teardown and assertion helpers.
    """

    def get_response_data(self, response) -> Dict[str, Any]:
        """
        Extract JSON data from response (handles both DRF Response and JsonResponse).

        The API returns JsonResponse with structure: {'code': 200, 'msg': '...', 'data': {...}}

        Args:
            response: Response object from API call

        Returns:
            Parsed JSON dictionary
        """
        if hasattr(response, 'data'):
            # DRF Response object
            return response.data
        elif hasattr(response, 'json'):
            # JsonResponse from test client
            return response.json()
        else:
            raise TypeError(f"Unexpected response type: {type(response)}")


class BaseMeetingTest(TestCommonMeeting):
    """
    Enhanced base class for standard meeting operations.

    Provides automatic user creation/cleanup and common assertion methods.
    """

    def setUp(self):
        """Set up test - create user and enable auth."""
        super().setUp()
        self.user = self.create_user()
        self.enable_client_auth(self.user.username)
        logger.info(f"Test setup complete: user={self.user.username}")

    def tearDown(self):
        """Clean up test - delete meetings and users."""
        self.clear_meetings()
        self.clear_all_users()
        logger.info("Test teardown complete")

    def assert_meeting_created(self, response, expected_data: Optional[Dict[str, Any]] = None):
        """
        Assert that a meeting was created successfully.

        Args:
            response: API response object
            expected_data: Optional dict of expected field values to verify
        """
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                        f"Expected 201, got {response.status_code}: {self.get_response_data(response)}")

        response_data = self.get_response_data(response)
        self.assertIn('data', response_data)

        if expected_data:
            for key, value in expected_data.items():
                self.assertEqual(response_data['data'].get(key), value,
                               f"Field '{key}' mismatch")

    def assert_meeting_updated(self, response, expected_changes: Optional[Dict[str, Any]] = None):
        """
        Assert that a meeting was updated successfully.

        Args:
            response: API response object
            expected_changes: Optional dict of expected changed values
        """
        self.assertEqual(response.status_code, status.HTTP_200_OK,
                        f"Expected 200, got {response.status_code}: {self.get_response_data(response)}")

        response_data = self.get_response_data(response)
        if expected_changes:
            for key, value in expected_changes.items():
                self.assertEqual(response_data['data'].get(key), value,
                               f"Field '{key}' was not updated correctly")

    def assert_meeting_deleted(self, response):
        """Assert that a meeting was deleted successfully."""
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT,
                        f"Expected 204, got {response.status_code}")

    def assert_validation_error(self, response, field_name: Optional[str] = None):
        """
        Assert that a validation error occurred.

        Args:
            response: API response object
            field_name: Optional specific field that should have error
        """
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                        f"Expected 400, got {response.status_code}: {response.data}")

        if field_name:
            self.assertIn('error', response.data,
                         "Response should contain error details")

    def assert_conflict_error(self, response):
        """Assert that a meeting conflict was detected."""
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
                        f"Expected 400 for conflict, got {response.status_code}")

    def get_meeting_from_response(self, response) -> Dict[str, Any]:
        """Extract meeting data from response."""
        response_data = self.get_response_data(response)
        self.assertIn('data', response_data)
        return response_data['data']


class BaseCyclicMeetingTest(BaseMeetingTest):
    """
    Base class for cyclic meeting tests.

    Provides specialized helpers for testing cyclic meetings, sub-meetings,
    and date expansion logic.
    """

    def assert_sub_meetings_created(self, parent_mid: str, expected_count: int):
        """
        Assert that the correct number of sub-meetings were created.

        Args:
            parent_mid: Parent meeting ID
            expected_count: Expected number of sub-meetings
        """
        sub_meetings = MeetingCycleSubMeeting.objects.filter(mid=parent_mid)
        actual_count = sub_meetings.count()

        self.assertEqual(actual_count, expected_count,
                        f"Expected {expected_count} sub-meetings, found {actual_count}")

        return sub_meetings

    def assert_cycle_date_created(self, parent_mid: str):
        """
        Assert that cycle date record was created.

        Args:
            parent_mid: Parent meeting ID

        Returns:
            MeetingCycleDate object
        """
        cycle_date = MeetingCycleDate.objects.filter(mid=parent_mid).first()
        self.assertIsNotNone(cycle_date,
                           f"No cycle date record found for meeting {parent_mid}")
        return cycle_date

    def assert_sub_meeting_dates_correct(self, sub_meetings, expected_dates: List[str]):
        """
        Verify that sub-meeting dates match expected expansion.

        Args:
            sub_meetings: QuerySet of MeetingCycleSubMeeting objects
            expected_dates: List of expected date strings (YYYY-MM-DD)
        """
        actual_dates = sorted([sm.date for sm in sub_meetings])
        expected_dates_sorted = sorted(expected_dates)

        self.assertEqual(actual_dates, expected_dates_sorted,
                        f"Sub-meeting dates don't match.\nExpected: {expected_dates_sorted}\nActual: {actual_dates}")

    def assert_sub_meeting_has_unique_sub_ids(self, sub_meetings):
        """Verify all sub-meetings have unique sub_ids."""
        sub_ids = [sm.sub_id for sm in sub_meetings]
        unique_sub_ids = set(sub_ids)

        self.assertEqual(len(sub_ids), len(unique_sub_ids),
                        f"Found duplicate sub_ids: {sub_ids}")

    def assert_sub_meeting_inherits_parent_properties(self, parent_meeting, sub_meeting_date_obj):
        """
        Verify sub-meeting inherits correct properties from parent.

        Args:
            parent_meeting: Parent Meeting object
            sub_meeting_date_obj: MeetingCycleSubMeeting object
        """
        self.assertEqual(sub_meeting_date_obj.mid, parent_meeting.mid,
                        "Sub-meeting mid doesn't match parent")
        # Times should match cycle_date start/end
        cycle_date = self.assert_cycle_date_created(parent_meeting.mid)
        self.assertEqual(sub_meeting_date_obj.start, cycle_date.start,
                        "Sub-meeting start time doesn't match cycle date")
        self.assertEqual(sub_meeting_date_obj.end, cycle_date.end,
                        "Sub-meeting end time doesn't match cycle date")

    def get_cyclic_meeting_with_details(self, mid: str) -> Dict[str, Any]:
        """
        Get cyclic meeting with all related records.

        Args:
            mid: Meeting ID

        Returns:
            Dict with meeting, cycle_date, and sub_meetings
        """
        meeting = Meeting.objects.filter(mid=mid).first()
        self.assertIsNotNone(meeting, f"Meeting {mid} not found")

        cycle_date = MeetingCycleDate.objects.filter(mid=mid).first()
        sub_meetings = MeetingCycleSubMeeting.objects.filter(mid=mid).all()

        return {
            'meeting': meeting,
            'cycle_date': cycle_date,
            'sub_meetings': list(sub_meetings)
        }

    def calculate_expected_daily_dates(self, start_date: str, end_date: str, interval: int) -> List[str]:
        """
        Calculate expected dates for daily cycle.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Day interval

        Returns:
            List of date strings
        """
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        dates = []
        current = start
        while current <= end:
            dates.append(str(current))
            current += timedelta(days=interval)

        return dates

    def calculate_expected_weekly_dates(
        self,
        start_date: str,
        end_date: str,
        interval: int,
        weekdays: List[int]
    ) -> List[str]:
        """
        Calculate expected dates for weekly cycle.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            interval: Week interval
            weekdays: List of weekday numbers (1=Mon, 7=Sun)

        Returns:
            List of date strings
        """

        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()

        dates = []
        current = start

        # Find first occurrence of each weekday
        while current <= end:
            # Check if current day is in the weekday list (1=Mon, 7=Sun)
            current_weekday = current.isoweekday()
            if current_weekday in weekdays:
                # Add this date and all subsequent occurrences
                week_date = current
                while week_date <= end:
                    dates.append(str(week_date))
                    week_date += timedelta(weeks=interval)
            current += timedelta(days=1)
            # Stop after checking first week
            if (current - start).days >= 7:
                break

        return sorted(dates)

    def assert_recording_records_created(self, mid: str, sub_id: Optional[str] = None):
        """
        Assert that recording records were created for a meeting.

        Args:
            mid: Meeting ID
            sub_id: Optional sub-meeting ID
        """
        obs_records = MeetingObsRecords.objects.filter(mid=mid)
        bili_records = MeetingBiliRecords.objects.filter(mid=mid)

        if sub_id:
            obs_records = obs_records.filter(sub_id=sub_id)
            bili_records = bili_records.filter(sub_id=sub_id)

        # At least one of the recording types should be created
        self.assertTrue(
            obs_records.exists() or bili_records.exists(),
            f"No recording records found for meeting {mid}"
        )
