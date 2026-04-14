#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
"""
Unit tests for meeting status functionality.

Tests include:
- DAO methods for status sync and management
- Force end meeting API endpoints
- Business status calculation logic
- Warning email deduplication
"""
import datetime
import logging
from unittest import mock
from datetime import timedelta

from rest_framework import status

from meeting.infrastructure.dao.meeting_dao import MeetingDao
from meeting.infrastructure.dao.meeting_cycle_sub_dao import MeetingCycleSubMeetingDao
from meeting.controller.serializers.meeting_serializers import calculate_business_status
from meeting.domain.primitive.meeting_status import BusinessMeetingStatus
from meeting_platform.test.meeting.test_base import TestCommonMeeting
from meeting.management.commands.handle_meeting_status import HandleMeetingStatus

logger = logging.getLogger("log")


class MeetingDaoStatusTest(TestCommonMeeting):
    """Test MeetingDao status-related methods."""

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
            "status": BusinessMeetingStatus.NOT_STARTED.value,  # 未开始
            "warning_email_sent": False,
        }
        defaults.update(kwargs)
        return MeetingDao.create(**defaults)

    def test_update_status_sets_flag_and_timestamp(self):
        """Test that update_status correctly sets status and timestamp."""
        meeting = self._create_test_meeting()

        # Update to ongoing
        MeetingDao.update_status(meeting.id, BusinessMeetingStatus.ONGOING.value)

        # Refresh from database
        meeting.refresh_from_db()

        self.assertEqual(meeting.status, BusinessMeetingStatus.ONGOING.value)
        self.assertIsNotNone(meeting.status_updated_at)

    def test_get_upcoming_end_meetings_filters_correctly(self):
        """Test that get_upcoming_end_meetings returns meetings ending soon."""
        now = datetime.datetime.now()
        soon_time = (now + timedelta(minutes=3)).strftime('%H:%M')
        later_time = (now + timedelta(minutes=30)).strftime('%H:%M')

        # Meeting ending soon with status=1 (ongoing)
        upcoming_meeting = self._create_test_meeting(
            end=soon_time,
            status=BusinessMeetingStatus.ONGOING.value,  # 进行中
            mid=f"upcoming_mid_{datetime.datetime.now().timestamp()}"
        )

        # Meeting ending later
        later_meeting = self._create_test_meeting(
            end=later_time,
            status=BusinessMeetingStatus.ONGOING.value,
            mid=f"later_mid_{datetime.datetime.now().timestamp()}"
        )

        # Meeting already sent warning email
        warned_meeting = self._create_test_meeting(
            end=soon_time,
            status=BusinessMeetingStatus.ONGOING.value,
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

    def test_clear_status_resets_all_fields(self):
        """Test that clear_status resets status and warning fields."""
        meeting = self._create_test_meeting(
            status=BusinessMeetingStatus.ONGOING.value,
            warning_email_sent=True
        )

        MeetingDao.clear_status(meeting.id)

        meeting.refresh_from_db()
        self.assertEqual(meeting.status, BusinessMeetingStatus.ENDED.value)  # 已结束
        self.assertFalse(meeting.warning_email_sent)
        self.assertIsNotNone(meeting.status_updated_at)

    def test_get_non_cycle_meetings(self):
        """Test that get_non_cycle_meetings returns non-cycle meetings."""
        meeting1 = self._create_test_meeting()
        meeting2 = self._create_test_meeting(
            mid=f"test_mid2_{datetime.datetime.now().timestamp()}"
        )

        result = list(MeetingDao.get_non_cycle_meetings(self.community, {}))

        self.assertEqual(len(result), 2)


class MeetingCycleSubMeetingDaoStatusTest(TestCommonMeeting):
    """Test MeetingCycleSubMeetingDao status-related methods."""

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
            "status": BusinessMeetingStatus.NOT_STARTED.value,
            "warning_email_sent": False,
        }
        defaults.update(kwargs)
        return MeetingCycleSubMeetingDao.create(**defaults)

    def test_update_status_for_sub_meeting(self):
        """Test updating status for sub meeting."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent)

        MeetingCycleSubMeetingDao.update_status(sub.id, BusinessMeetingStatus.ONGOING.value)

        sub.refresh_from_db()
        self.assertEqual(sub.status, BusinessMeetingStatus.ONGOING.value)
        self.assertIsNotNone(sub.status_updated_at)

    def test_mark_warning_email_sent_for_sub_meeting(self):
        """Test marking warning email sent for sub meeting."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent)

        MeetingCycleSubMeetingDao.mark_warning_email_sent(sub.id)

        sub.refresh_from_db()
        self.assertTrue(sub.warning_email_sent)

    def test_clear_status_for_sub_meeting(self):
        """Test clearing status for sub meeting."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(
            parent,
            status=BusinessMeetingStatus.ONGOING.value,
            warning_email_sent=True
        )

        MeetingCycleSubMeetingDao.clear_status(sub.sub_id)

        sub.refresh_from_db()
        self.assertEqual(sub.status, BusinessMeetingStatus.ENDED.value)  # 已结束
        self.assertFalse(sub.warning_email_sent)

    def test_get_expanded_sub_meetings(self):
        """Test getting expanded sub meetings."""
        parent = self._create_parent_meeting()
        sub1 = self._create_sub_meeting(parent)
        sub2 = self._create_sub_meeting(
            parent,
            sub_id=f"sub2_{datetime.datetime.now().timestamp()}"
        )

        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings(self.community, {})

        self.assertEqual(len(result), 2)
        self.assertTrue(all(item['is_cycle'] for item in result))


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
            "status": BusinessMeetingStatus.ONGOING.value,  # 进行中
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

        # Verify status was cleared
        meeting.refresh_from_db()
        self.assertEqual(meeting.status, BusinessMeetingStatus.ENDED.value)  # 已结束
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
            status=BusinessMeetingStatus.ONGOING.value  # 进行中
        )
        sub2 = MeetingCycleSubMeetingDao.create(
            mid=parent.mid,
            sub_id=f"sub2_{datetime.datetime.now().timestamp()}",
            date=self.today,
            start="14:00",
            end="15:00",
            meeting=parent,
            status=BusinessMeetingStatus.ONGOING.value  # 进行中
        )

        response = self.client.post(self.url, {"meeting_id": parent.id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify all sub meetings were cleared
        sub1.refresh_from_db()
        sub2.refresh_from_db()
        self.assertEqual(sub1.status, BusinessMeetingStatus.ENDED.value)  # 已结束
        self.assertEqual(sub2.status, BusinessMeetingStatus.ENDED.value)  # 已结束

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
            status=BusinessMeetingStatus.ONGOING.value,  # 进行中
            warning_email_sent=True
        )

        response = self.client.post(self.url, {"meeting_id": parent.id, "sub_id": sub.sub_id})

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify status was cleared
        sub.refresh_from_db()
        self.assertEqual(sub.status, BusinessMeetingStatus.ENDED.value)  # 已结束
        self.assertFalse(sub.warning_email_sent)

    def test_force_end_sub_meeting_not_found(self):
        """Test force end of non-existent sub meeting returns error."""
        meeting = self._create_test_meeting(is_cycle=True)
        response = self.client.post(self.url, {"meeting_id": meeting.id, "sub_id": "non_existent_sub_id"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class BusinessStatusCalculationTest(TestCommonMeeting):
    """Test the business status calculation logic."""

    def setUp(self):
        super().setUp()
        self.now = datetime.datetime(2026, 4, 9, 10, 30)  # Fixed time for testing
        self.today = self.now.strftime('%Y-%m-%d')

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def test_status_not_started(self):
        """Test business status 0 - not started."""
        # Meeting starts at 11:00, current time is 10:30
        meeting_data = {
            'date': self.today,
            'start': '11:00',
            'end': '12:00',
            'status': BusinessMeetingStatus.NOT_STARTED.value  # 数据库状态：未开始
        }

        result = calculate_business_status(meeting_data, self.now)
        self.assertEqual(result, BusinessMeetingStatus.NOT_STARTED.value)

    def test_status_ongoing(self):
        """Test business status 1 - ongoing."""
        # Meeting is 10:00-11:00, current time is 10:30, status=1
        meeting_data = {
            'date': self.today,
            'start': '10:00',
            'end': '11:00',
            'status': BusinessMeetingStatus.ONGOING.value  # 数据库状态：进行中
        }

        result = calculate_business_status(meeting_data, self.now)
        self.assertEqual(result, BusinessMeetingStatus.ONGOING.value)

    def test_status_ended(self):
        """Test business status 2 - ended."""
        # Meeting ended at 10:00, current time is 10:30, status=2
        meeting_data = {
            'date': self.today,
            'start': '09:00',
            'end': '10:00',
            'status': BusinessMeetingStatus.ENDED.value  # 数据库状态：已结束
        }

        result = calculate_business_status(meeting_data, self.now)
        self.assertEqual(result, BusinessMeetingStatus.ENDED.value)

    def test_status_overtime(self):
        """Test business status 3 - overtime."""
        # Meeting ended at 10:00, current time is 10:30, but status=1 (still ongoing in API)
        meeting_data = {
            'date': self.today,
            'start': '09:00',
            'end': '10:00',
            'status': BusinessMeetingStatus.ONGOING.value  # 数据库状态：进行中（但已超时）
        }

        result = calculate_business_status(meeting_data, self.now)
        self.assertEqual(result, BusinessMeetingStatus.OVERTIME.value)

    def test_status_with_missing_data(self):
        """Test business status with missing date/time data."""
        meeting_data = {
            'date': None,
            'start': '10:00',
            'end': '11:00',
            'status': BusinessMeetingStatus.NOT_STARTED.value
        }

        result = calculate_business_status(meeting_data, self.now)
        self.assertEqual(result, BusinessMeetingStatus.NOT_STARTED.value)  # 默认未开始

    def test_status_cancelled(self):
        """Test business status 4 - cancelled (is_delete=True)."""
        # Meeting is deleted
        meeting_data = {
            'date': self.today,
            'start': '09:00',
            'end': '10:00',
            'status': BusinessMeetingStatus.NOT_STARTED.value,
            'is_delete': True
        }

        result = calculate_business_status(meeting_data, self.now)
        self.assertEqual(result, BusinessMeetingStatus.CANCELLED.value)


class MeetingListViewTest(TestCommonMeeting):
    """Test the merged meeting list API endpoint."""

    url = "/inner/v1/meeting/meeting/list/"

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
            "status": BusinessMeetingStatus.NOT_STARTED.value,
        }
        defaults.update(kwargs)
        return MeetingDao.create(**defaults)

    def test_list_meetings_requires_community(self):
        """Test that community parameter is required."""
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_meetings_returns_non_cycle_meetings(self):
        """Test that list returns non-cycle meetings."""
        meeting = self._create_test_meeting()

        response = self.client.get(f"{self.url}?community={self.community}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json() if hasattr(response, 'json') else response.data
        self.assertIn('data', data)
        self.assertIn('list', data['data'])
        self.assertEqual(len(data['data']['list']), 1)

    def test_list_meetings_includes_status(self):
        """Test that meeting list includes business status."""
        meeting = self._create_test_meeting()

        response = self.client.get(f"{self.url}?community={self.community}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json() if hasattr(response, 'json') else response.data
        meeting_data = data['data']['list'][0]
        self.assertIn('status', meeting_data)
        self.assertIn('is_cycle', meeting_data)

    def test_list_meetings_filter_by_date(self):
        """Test filtering meetings by date."""
        meeting = self._create_test_meeting()

        response = self.client.get(f"{self.url}?community={self.community}&date={self.today}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json() if hasattr(response, 'json') else response.data
        self.assertEqual(len(data['data']['list']), 1)


# Import CreateMeetingViewTest data for reuse


class SmartWarningEmailTest(TestCommonMeeting):
    """Test simplified warning email logic."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')
        # Clear any existing meeting data to ensure clean test environment
        self.clear_meetings()

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
            "status": BusinessMeetingStatus.ONGOING.value,  # 进行中
            "warning_email_sent": False,
        }
        defaults.update(kwargs)
        return MeetingDao.create(**defaults)

    def test_get_ongoing_meetings_for_warning(self):
        """Test that get_ongoing_meetings_for_warning returns ongoing/overtime meetings."""
        # Use unique host_id to avoid data race with other tests
        unique_host_id = f"warning_test_{datetime.datetime.now().timestamp()}@example.com"
        now = datetime.datetime.now()
        current_time = now.strftime('%H:%M')

        # Create ongoing meeting (status=1)
        ongoing_meeting = self._create_test_meeting(
            end="23:00",  # End after current time
            status=BusinessMeetingStatus.ONGOING.value,
            host_id=unique_host_id,
            mid=f"ongoing_mid_{datetime.datetime.now().timestamp()}"
        )

        # Create overtime meeting (status=3)
        overtime_meeting = self._create_test_meeting(
            end="23:00",
            status=BusinessMeetingStatus.OVERTIME.value,
            host_id=unique_host_id,
            mid=f"overtime_mid_{datetime.datetime.now().timestamp()}"
        )

        # Create meeting that already sent warning
        warned_meeting = self._create_test_meeting(
            end="23:00",
            status=BusinessMeetingStatus.ONGOING.value,
            warning_email_sent=True,
            host_id=unique_host_id,
            mid=f"warned_mid_{datetime.datetime.now().timestamp()}"
        )

        # Create ended meeting (should not be included)
        ended_meeting = self._create_test_meeting(
            end="23:00",
            status=BusinessMeetingStatus.ENDED.value,
            host_id=unique_host_id,
            mid=f"ended_mid_{datetime.datetime.now().timestamp()}"
        )

        result = MeetingDao.get_ongoing_meetings_for_warning(self.community, self.today)

        # Should include ongoing and overtime meetings without warning sent
        result_ids = [m.id for m in result]
        self.assertIn(ongoing_meeting.id, result_ids)
        self.assertIn(overtime_meeting.id, result_ids)
        self.assertNotIn(warned_meeting.id, result_ids)
        self.assertNotIn(ended_meeting.id, result_ids)

    def test_get_next_meeting_start_time(self):
        """Test that get_next_meeting_start_time returns the earliest next meeting."""
        # Use unique host_id to avoid data race with other tests
        host_id = f"next_test_{datetime.datetime.now().timestamp()}@example.com"

        # Create current meeting ending at 11:00
        current_meeting = self._create_test_meeting(
            end="11:00",
            host_id=host_id,
            mid=f"current_mid_{datetime.datetime.now().timestamp()}"
        )

        # Create subsequent meeting starting at 14:00
        next_meeting1 = self._create_test_meeting(
            start="14:00",
            end="15:00",
            host_id=host_id,
            mid=f"next1_mid_{datetime.datetime.now().timestamp()}"
        )

        # Create another subsequent meeting starting at 16:00
        next_meeting2 = self._create_test_meeting(
            start="16:00",
            end="17:00",
            host_id=host_id,
            mid=f"next2_mid_{datetime.datetime.now().timestamp()}"
        )

        result = MeetingDao.get_next_meeting_start_time(
            self.community, host_id, self.today, "11:00"
        )

        # Should return the earliest next meeting start time
        self.assertEqual(result, "14:00")

    def test_get_next_meeting_start_time_no_subsequent(self):
        """Test that get_next_meeting_start_time returns None when no subsequent meetings."""
        # Use unique host_id to avoid data race with other tests
        host_id = f"no_subsequent_test_{datetime.datetime.now().timestamp()}@example.com"

        # Create a meeting without subsequent meetings
        meeting = self._create_test_meeting(
            host_id=host_id,
            mid=f"single_mid_{datetime.datetime.now().timestamp()}"
        )

        result = MeetingDao.get_next_meeting_start_time(
            self.community, host_id, self.today, "11:00"
        )

        self.assertIsNone(result)

    def test_should_send_warning_before_next_meeting(self):
        """Test warning timing - should send 30 minutes before next meeting starts.

        简化逻辑：无论间隔长短，都在下一场会议开始前30分钟发送预警
        """
        from meeting.management.commands.handle_meeting_status import HandleMeetingStatus

        handler = HandleMeetingStatus(self.community)

        # 场景：会议A 09:00-10:00，会议B 14:00-15:00
        # 预警时间：14:00 - 30分钟 = 13:30 发送预警

        # At 13:30, should send warning (center of window)
        now_1330 = datetime.datetime.strptime(f"{self.today} 13:30", "%Y-%m-%d %H:%M")
        result = handler._should_send_warning("14:00", now_1330)
        self.assertTrue(result)

        # At 13:31:01, should NOT send warning (61 seconds away, outside 60s tolerance)
        now_133101 = datetime.datetime.strptime(f"{self.today} 13:31:01", "%Y-%m-%d %H:%M:%S")
        result = handler._should_send_warning("14:00", now_133101)
        self.assertFalse(result)

        # At 13:28:59, should NOT send warning (61 seconds away)
        now_132859 = datetime.datetime.strptime(f"{self.today} 13:28:59", "%Y-%m-%d %H:%M:%S")
        result = handler._should_send_warning("14:00", now_132859)
        self.assertFalse(result)

    def test_should_send_warning_short_interval(self):
        """Test warning timing when interval is short.

        场景：会议A 09:00-10:00，会议B 11:00-12:00（间隔1小时）
        预警时间：11:00 - 30分钟 = 10:30 发送预警
        """


        handler = HandleMeetingStatus(self.community)

        # At 10:30, should send warning (center of window)
        now_1030 = datetime.datetime.strptime(f"{self.today} 10:30", "%Y-%m-%d %H:%M")
        result = handler._should_send_warning("11:00", now_1030)
        self.assertTrue(result)

        # At 10:31:01, should NOT send warning (61 seconds away)
        now_103101 = datetime.datetime.strptime(f"{self.today} 10:31:01", "%Y-%m-%d %H:%M:%S")
        result = handler._should_send_warning("11:00", now_103101)
        self.assertFalse(result)

        # At 09:50, should NOT send warning (not the right time - 40 minutes before warning time)
        now_0950 = datetime.datetime.strptime(f"{self.today} 09:50", "%Y-%m-%d %H:%M")
        result = handler._should_send_warning("11:00", now_0950)
        self.assertFalse(result)

    def test_should_send_warning_long_interval(self):
        """Test warning timing when interval is long.

        场景：会议A 09:00-10:00，会议B 16:00-17:00（间隔6小时）
        预警时间：16:00 - 30分钟 = 15:30 发送预警
        """
        from meeting.management.commands.handle_meeting_status import HandleMeetingStatus

        handler = HandleMeetingStatus(self.community)

        # At 15:30, should send warning
        now_1530 = datetime.datetime.strptime(f"{self.today} 15:30", "%Y-%m-%d %H:%M")
        result = handler._should_send_warning("16:00", now_1530)
        self.assertTrue(result)

        # At 09:50, should NOT send warning (not the right time - nearly 6 hours away)
        now_0950 = datetime.datetime.strptime(f"{self.today} 09:50", "%Y-%m-%d %H:%M")
        result = handler._should_send_warning("16:00", now_0950)
        self.assertFalse(result)

        # At 15:31:01, should NOT send warning (61 seconds away)
        now_153101 = datetime.datetime.strptime(f"{self.today} 15:31:01", "%Y-%m-%d %H:%M:%S")
        result = handler._should_send_warning("16:00", now_153101)
        self.assertFalse(result)

    def test_get_next_sub_meeting_start_time(self):
        """Test that get_next_sub_meeting_start_time returns correct time."""
        # Use unique host_id to avoid data race with other tests
        host_id = f"cycle_test_{datetime.datetime.now().timestamp()}@example.com"

        # Create parent meeting
        parent = MeetingDao.create(
            sponsor="test_sponsor",
            group_name="test_group",
            community=self.community,
            topic="Test Cycle Meeting",
            platform="WELINK",
            is_cycle=True,
            is_record=False,
            mid=f"cycle_mid_{datetime.datetime.now().timestamp()}",
            host_id=host_id,
        )

        # Create subsequent sub meeting
        sub = MeetingCycleSubMeetingDao.create(
            mid=parent.mid,
            sub_id=f"sub_{datetime.datetime.now().timestamp()}",
            date=self.today,
            start="14:00",
            end="15:00",
            meeting=parent,
            status=BusinessMeetingStatus.NOT_STARTED.value,
        )

        result = MeetingCycleSubMeetingDao.get_next_sub_meeting_start_time(
            self.community, host_id, self.today, "11:00"
        )

        self.assertEqual(result, "14:00")


class MeetingAppSponsorsTest(TestCommonMeeting):
    """Test MeetingApp.get_meeting_sponsors method."""

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
            "status": BusinessMeetingStatus.NOT_STARTED.value,
        }
        defaults.update(kwargs)
        return MeetingDao.create(**defaults)

    def test_get_meeting_sponsors_basic(self):
        """Test basic sponsor list retrieval."""
        from meeting.application.meeting import MeetingApp

        # Create meetings with different sponsors
        self._create_test_meeting(sponsor="Alice")
        self._create_test_meeting(sponsor="Bob", mid=f"mid2_{datetime.datetime.now().timestamp()}")
        self._create_test_meeting(sponsor="Charlie", mid=f"mid3_{datetime.datetime.now().timestamp()}")

        app = MeetingApp()
        result = app.get_meeting_sponsors(self.community)

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 3)
        self.assertIn("Alice", result)
        self.assertIn("Bob", result)
        self.assertIn("Charlie", result)

    def test_get_meeting_sponsors_with_keyword(self):
        """Test sponsor list with keyword filter."""
        from meeting.application.meeting import MeetingApp

        # Create meetings with different sponsors
        self._create_test_meeting(sponsor="Alice_Smith")
        self._create_test_meeting(sponsor="Bob_Jones", mid=f"mid2_{datetime.datetime.now().timestamp()}")
        self._create_test_meeting(sponsor="Charlie_Brown", mid=f"mid3_{datetime.datetime.now().timestamp()}")

        app = MeetingApp()
        # Filter by keyword
        result = app.get_meeting_sponsors(self.community, sponsor_keyword="Smith")

        self.assertEqual(len(result), 1)
        self.assertIn("Alice_Smith", result)

    def test_get_meeting_sponsors_deduplication(self):
        """Test sponsor list deduplication."""
        from meeting.application.meeting import MeetingApp

        # Create multiple meetings with same sponsor
        self._create_test_meeting(sponsor="Alice")
        self._create_test_meeting(sponsor="Alice", mid=f"mid2_{datetime.datetime.now().timestamp()}")
        self._create_test_meeting(sponsor="Alice", mid=f"mid3_{datetime.datetime.now().timestamp()}")

        app = MeetingApp()
        result = app.get_meeting_sponsors(self.community)

        # Should only return one unique sponsor
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], "Alice")

    def test_get_meeting_sponsors_empty_community(self):
        """Test sponsor list for community with no meetings."""
        from meeting.application.meeting import MeetingApp

        app = MeetingApp()
        result = app.get_meeting_sponsors("nonexistent_community")

        self.assertEqual(result, [])

    def test_get_meeting_sponsors_sorted(self):
        """Test that sponsor list is sorted."""
        from meeting.application.meeting import MeetingApp

        # Create meetings with sponsors in non-alphabetical order
        self._create_test_meeting(sponsor="Zebra")
        self._create_test_meeting(sponsor="Alpha", mid=f"mid2_{datetime.datetime.now().timestamp()}")
        self._create_test_meeting(sponsor="Middle", mid=f"mid3_{datetime.datetime.now().timestamp()}")

        app = MeetingApp()
        result = app.get_meeting_sponsors(self.community)

        # Should be sorted alphabetically
        self.assertEqual(result, ["Alpha", "Middle", "Zebra"])


class MeetingAppForceStopMeetingTest(TestCommonMeeting):
    """Test MeetingApp.force_stop_meeting method."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')
        self.user = self.create_user()
        self.enable_client_auth(self.user.username)

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
    def test_force_stop_non_cycle_meeting(self, mock_force_end):
        """Test force stopping a non-cycle meeting."""
        from meeting.application.meeting import MeetingApp

        mock_force_end.return_value = 200
        meeting = self._create_test_meeting(status=BusinessMeetingStatus.ONGOING.value)

        app = MeetingApp()
        result = app.force_stop_meeting(meeting.id, sub_id=None)

        self.assertTrue(result)
        meeting.refresh_from_db()
        self.assertEqual(meeting.status, BusinessMeetingStatus.ENDED.value)
        self.assertFalse(meeting.warning_email_sent)

    def test_force_stop_meeting_invalid_meeting_id(self):
        """Test force stopping with invalid meeting_id."""
        from meeting.application.meeting import MeetingApp
        from meeting_platform.utils.ret_api import MyValidationError

        app = MeetingApp()
        with self.assertRaises(MyValidationError):
            app.force_stop_meeting(99999, sub_id=None)

    @mock.patch("meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.force_end_meeting")
    def test_force_stop_cycle_meeting_clears_all_ongoing_sub_meetings(self, mock_force_end):
        """Test force stopping cycle meeting clears all ongoing sub meetings."""
        from meeting.application.meeting import MeetingApp

        mock_force_end.return_value = 200

        parent = self._create_parent_meeting()
        sub1 = self._create_sub_meeting(parent, status=BusinessMeetingStatus.ONGOING.value)
        sub2 = self._create_sub_meeting(parent, status=BusinessMeetingStatus.ONGOING.value,
                                        sub_id=f"sub2_{datetime.datetime.now().timestamp()}")
        # Create a non-ongoing sub meeting - should not be cleared
        sub3 = self._create_sub_meeting(parent, status=BusinessMeetingStatus.NOT_STARTED.value,
                                        sub_id=f"sub3_{datetime.datetime.now().timestamp()}")

        app = MeetingApp()
        result = app.force_stop_meeting(parent.id, sub_id=None)

        self.assertTrue(result)
        sub1.refresh_from_db()
        sub2.refresh_from_db()
        sub3.refresh_from_db()
        self.assertEqual(sub1.status, BusinessMeetingStatus.ENDED.value)
        self.assertEqual(sub2.status, BusinessMeetingStatus.ENDED.value)
        # Non-ongoing sub meeting should remain unchanged
        self.assertEqual(sub3.status, BusinessMeetingStatus.NOT_STARTED.value)

    @mock.patch("meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.force_end_meeting")
    def test_force_stop_specific_sub_meeting(self, mock_force_end):
        """Test force stopping a specific sub meeting."""
        from meeting.application.meeting import MeetingApp

        mock_force_end.return_value = 200

        parent = self._create_parent_meeting()
        sub1 = self._create_sub_meeting(parent, status=BusinessMeetingStatus.ONGOING.value)
        sub2 = self._create_sub_meeting(parent, status=BusinessMeetingStatus.ONGOING.value,
                                        sub_id=f"sub2_{datetime.datetime.now().timestamp()}")

        app = MeetingApp()
        result = app.force_stop_meeting(parent.id, sub_id=sub1.sub_id)

        self.assertTrue(result)
        sub1.refresh_from_db()
        sub2.refresh_from_db()
        # Only specified sub meeting should be cleared
        self.assertEqual(sub1.status, BusinessMeetingStatus.ENDED.value)
        # Other sub meeting should remain unchanged
        self.assertEqual(sub2.status, BusinessMeetingStatus.ONGOING.value)

    def test_force_stop_sub_meeting_invalid_sub_id(self):
        """Test force stopping with invalid sub_id."""
        from meeting.application.meeting import MeetingApp
        from meeting_platform.utils.ret_api import MyValidationError

        parent = self._create_parent_meeting()

        app = MeetingApp()
        with self.assertRaises(MyValidationError):
            app.force_stop_meeting(parent.id, sub_id="nonexistent_sub_id")


class MeetingAppMergedMeetingListTest(TestCommonMeeting):
    """Test MeetingApp.get_merged_meeting_list method."""

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
            "status": BusinessMeetingStatus.NOT_STARTED.value,
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
            "status": BusinessMeetingStatus.NOT_STARTED.value,
        }
        defaults.update(kwargs)
        return MeetingCycleSubMeetingDao.create(**defaults)

    def test_merged_meeting_list_pagination_default(self):
        """Test merged meeting list with default pagination."""
        from meeting.application.meeting import MeetingApp

        # Create some meetings
        self._create_test_meeting()
        self._create_test_meeting(mid=f"mid2_{datetime.datetime.now().timestamp()}")

        app = MeetingApp()
        result = app.get_merged_meeting_list(self.community, {})

        self.assertIn('total', result)
        self.assertIn('list', result)
        self.assertIn('page', result)
        self.assertIn('size', result)
        self.assertEqual(result['page'], 1)
        self.assertEqual(result['size'], 10)

    def test_merged_meeting_list_pagination_page_less_than_one(self):
        """Test merged meeting list corrects page < 1 to 1."""
        from meeting.application.meeting import MeetingApp

        self._create_test_meeting()

        app = MeetingApp()
        result = app.get_merged_meeting_list(self.community, {}, page=0)

        self.assertEqual(result['page'], 1)

    def test_merged_meeting_list_pagination_page_size_limit(self):
        """Test merged meeting list corrects page_size > 100 to 10."""
        from meeting.application.meeting import MeetingApp

        self._create_test_meeting()

        app = MeetingApp()
        result = app.get_merged_meeting_list(self.community, {}, page_size=150)

        self.assertEqual(result['size'], 10)

    def test_merged_meeting_list_invalid_order_by_defaults_to_date(self):
        """Test merged meeting list defaults invalid order_by to 'date'."""
        from meeting.application.meeting import MeetingApp

        self._create_test_meeting()

        app = MeetingApp()
        result = app.get_merged_meeting_list(self.community, {}, order_by='invalid_field')

        # Should work without error, defaulting to 'date'
        self.assertIn('list', result)

    def test_merged_meeting_list_includes_cycle_info(self):
        """Test merged meeting list includes cycle info for cycle meetings."""
        from meeting.application.meeting import MeetingApp
        from meeting.infrastructure.dao.meeting_cycle_dao import MeetingCycleDao

        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent)

        # Create cycle date record
        MeetingCycleDao.create(
            mid=parent.mid,
            start_date="2026-04-01",
            end_date="2026-04-30",
            start="10:00",
            end="11:00",
            cycle_type=1,
            interval=1,
            meeting=parent
        )

        app = MeetingApp()
        result = app.get_merged_meeting_list(self.community, {})

        # Find the cycle meeting in the result
        cycle_meetings = [m for m in result['list'] if m.get('is_cycle')]
        self.assertTrue(len(cycle_meetings) > 0)

        cycle_meeting = cycle_meetings[0]
        self.assertIn('cycle_start_date', cycle_meeting)
        self.assertIn('cycle_end_date', cycle_meeting)
        self.assertIn('cycle_start', cycle_meeting)
        self.assertIn('cycle_end', cycle_meeting)

    def test_merged_meeting_list_filter_by_date(self):
        """Test merged meeting list filter by date."""
        from meeting.application.meeting import MeetingApp

        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        # Create meeting today and tomorrow
        meeting_today = self._create_test_meeting()
        meeting_tomorrow = self._create_test_meeting(
            date=tomorrow,
            mid=f"mid2_{datetime.datetime.now().timestamp()}"
        )

        app = MeetingApp()
        result = app.get_merged_meeting_list(self.community, {'date': self.today})

        # Should only return today's meeting
        self.assertEqual(result['total'], 1)

    def test_merged_meeting_list_sort_asc(self):
        """Test merged meeting list ascending sort."""
        from meeting.application.meeting import MeetingApp

        # Create meetings with different dates
        yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        self._create_test_meeting(date=yesterday, mid=f"mid1_{datetime.datetime.now().timestamp()}")
        self._create_test_meeting(date=tomorrow, mid=f"mid2_{datetime.datetime.now().timestamp()}")

        app = MeetingApp()
        result = app.get_merged_meeting_list(self.community, {}, order_by='date', order_type='asc')

        dates = [m['date'] for m in result['list']]
        self.assertEqual(dates, sorted(dates))

    def test_merged_meeting_list_sort_desc(self):
        """Test merged meeting list descending sort."""
        from meeting.application.meeting import MeetingApp

        # Create meetings with different dates
        yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        self._create_test_meeting(date=yesterday, mid=f"mid1_{datetime.datetime.now().timestamp()}")
        self._create_test_meeting(date=tomorrow, mid=f"mid2_{datetime.datetime.now().timestamp()}")

        app = MeetingApp()
        result = app.get_merged_meeting_list(self.community, {}, order_by='date', order_type='desc')

        dates = [m['date'] for m in result['list']]
        self.assertEqual(dates, sorted(dates, reverse=True))


class MeetingAppDeleteDaoTest(TestCommonMeeting):
    """Test MeetingApp._delete_dao method for cycle meeting deletion."""

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
            "status": BusinessMeetingStatus.NOT_STARTED.value,
            "sequence": 0,
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
            "sequence": 0,
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
            "status": BusinessMeetingStatus.NOT_STARTED.value,
        }
        defaults.update(kwargs)
        return MeetingCycleSubMeetingDao.create(**defaults)

    def test_delete_dao_cycle_meeting_updates_sub_meetings_to_cancelled(self):
        """Test that deleting cycle meeting updates all sub meetings to CANCELLED."""
        from meeting.application.meeting import MeetingApp

        parent = self._create_parent_meeting()
        sub1 = self._create_sub_meeting(parent, status=BusinessMeetingStatus.ONGOING.value)
        sub2 = self._create_sub_meeting(parent, status=BusinessMeetingStatus.NOT_STARTED.value,
                                        sub_id=f"sub2_{datetime.datetime.now().timestamp()}")

        meeting_dict = {
            "mid": parent.mid,
            "is_cycle": True,
            "sequence": 1,
        }

        app = MeetingApp()
        result = app._delete_dao(parent.id, meeting_dict)

        self.assertEqual(result, parent.id)

        # Check that all sub meetings are marked as CANCELLED
        sub1.refresh_from_db()
        sub2.refresh_from_db()
        self.assertEqual(sub1.status, BusinessMeetingStatus.CANCELLED.value)
        self.assertEqual(sub2.status, BusinessMeetingStatus.CANCELLED.value)

    def test_delete_dao_non_cycle_meeting_no_sub_meeting_update(self):
        """Test that deleting non-cycle meeting does not affect sub meetings."""
        from meeting.application.meeting import MeetingApp

        meeting = self._create_test_meeting(is_cycle=False)

        meeting_dict = {
            "mid": meeting.mid,
            "is_cycle": False,
            "sequence": 1,
        }

        app = MeetingApp()
        result = app._delete_dao(meeting.id, meeting_dict)

        self.assertEqual(result, meeting.id)

        # Verify meeting is marked as deleted
        meeting.refresh_from_db()
        self.assertEqual(meeting.is_delete, 1)
        self.assertEqual(meeting.status, BusinessMeetingStatus.CANCELLED.value)