#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
"""
Unit tests for MeetingApp class methods.

Tests include:
- force_stop_meeting: non-cycle and cycle meeting scenarios
- get_merged_meeting_list: pagination, filters, ordering
- get_meeting_sponsors: basic and keyword search
- _delete_dao: cycle meeting deletion
"""
import datetime
from unittest import mock

from django.forms import model_to_dict
from django.test import RequestFactory

from meeting.application.meeting import MeetingApp
from meeting.infrastructure.dao.meeting_dao import MeetingDao
from meeting.infrastructure.dao.meeting_cycle_dao import MeetingCycleDao
from meeting.infrastructure.dao.meeting_cycle_sub_dao import MeetingCycleSubMeetingDao
from meeting.domain.primitive.meeting_status import BusinessMeetingStatus
from meeting.domain.primitive.cycle_type import CycleType
from meeting_platform.test.meeting.test_base import TestCommonMeeting
from meeting_platform.utils.ret_api import MyValidationError
from meeting_platform.utils.ret_code import RetCode


class MeetingAppForceStopTest(TestCommonMeeting):
    """Test MeetingApp.force_stop_meeting method."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')
        self.app = MeetingApp()

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def _create_non_cycle_meeting(self, **kwargs):
        """Create a non-cycle test meeting."""
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

    def _create_cycle_meeting(self, **kwargs):
        """Create a cycle test meeting with sub meetings."""
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
        parent = MeetingDao.create(**defaults)

        # Create cycle date
        MeetingCycleDao.create(
            mid=parent.mid,
            start_date=self.today,
            end_date=(datetime.datetime.now() + datetime.timedelta(days=7)).strftime('%Y-%m-%d'),
            start="10:00",
            end="11:00",
            cycle_type=CycleType.DAY.value,
            interval=1,
            meeting=parent
        )

        return parent

    def _create_sub_meeting(self, parent_meeting, **kwargs):
        """Create a sub meeting for cycle meeting."""
        defaults = {
            "mid": parent_meeting.mid,
            "sub_id": f"sub_{datetime.datetime.now().timestamp()}",
            "date": self.today,
            "start": "10:00",
            "end": "11:00",
            "meeting": parent_meeting,
            "status": BusinessMeetingStatus.ONGOING.value,
        }
        defaults.update(kwargs)
        return MeetingCycleSubMeetingDao.create(**defaults)

    @mock.patch('meeting.application.meeting.MeetingAdapterImpl.force_end_meeting')
    @mock.patch('meeting.infrastructure.dao.meeting_dao.MeetingDao.clear_status')
    def test_force_stop_non_cycle_meeting(self, mock_clear_status, mock_force_end):
        """Test force_stop_meeting for non-cycle meeting."""
        meeting = self._create_non_cycle_meeting()

        result = self.app.force_stop_meeting(meeting.id, None)

        self.assertTrue(result)
        mock_force_end.assert_called_once()
        mock_clear_status.assert_called_once_with(meeting.id)

    @mock.patch('meeting.application.meeting.MeetingAdapterImpl.force_end_meeting')
    @mock.patch('meeting.infrastructure.dao.meeting_cycle_sub_dao.MeetingCycleSubMeetingDao.clear_status')
    @mock.patch('meeting.infrastructure.dao.meeting_cycle_sub_dao.MeetingCycleSubMeetingDao.get_all')
    def test_force_stop_cycle_with_sub_id(self, mock_get_all, mock_clear_status, mock_force_end):
        """Test force_stop_meeting for cycle meeting with sub_id."""
        parent = self._create_cycle_meeting()
        sub = self._create_sub_meeting(parent)

        # Mock get_all to return the sub meeting
        mock_queryset = mock.MagicMock()
        mock_queryset.filter.return_value.first.return_value = sub
        mock_get_all.return_value = mock_queryset

        result = self.app.force_stop_meeting(parent.id, sub.sub_id)

        self.assertTrue(result)
        mock_force_end.assert_called_once()
        mock_clear_status.assert_called_once_with(sub.sub_id)

    @mock.patch('meeting.application.meeting.MeetingAdapterImpl.force_end_meeting')
    @mock.patch('meeting.infrastructure.dao.meeting_cycle_sub_dao.MeetingCycleSubMeetingDao.clear_status')
    @mock.patch('meeting.infrastructure.dao.meeting_cycle_sub_dao.MeetingCycleSubMeetingDao.get_by_mid')
    def test_force_stop_cycle_all_sub_meetings(self, mock_get_by_mid, mock_clear_status, mock_force_end):
        """Test force_stop_meeting for cycle meeting without sub_id clears all ongoing sub meetings."""
        parent = self._create_cycle_meeting()
        sub1 = self._create_sub_meeting(parent, status=BusinessMeetingStatus.ONGOING.value)
        sub2 = self._create_sub_meeting(parent, sub_id=f"sub2_{datetime.datetime.now().timestamp()}",
                                         status=BusinessMeetingStatus.NOT_STARTED.value)

        # Mock get_by_mid to return sub meetings
        mock_get_by_mid.return_value = [
            {'sub_id': sub1.sub_id, 'status': BusinessMeetingStatus.ONGOING.value},
            {'sub_id': sub2.sub_id, 'status': BusinessMeetingStatus.NOT_STARTED.value},
        ]

        result = self.app.force_stop_meeting(parent.id, None)

        self.assertTrue(result)
        mock_force_end.assert_called_once()
        # clear_status should be called for ongoing sub meeting only
        mock_clear_status.assert_called_once_with(sub1.sub_id)

    def test_force_stop_meeting_not_found(self):
        """Test force_stop_meeting raises error for nonexistent meeting."""
        with self.assertRaises(MyValidationError) as context:
            self.app.force_stop_meeting(99999, None)

        self.assertEqual(context.exception.detail_code, RetCode.STATUS_PARAMETER_ERROR)

    @mock.patch('meeting.infrastructure.dao.meeting_cycle_sub_dao.MeetingCycleSubMeetingDao.get_all')
    def test_force_stop_sub_meeting_not_found(self, mock_get_all):
        """Test force_stop_meeting raises error for nonexistent sub meeting."""
        parent = self._create_cycle_meeting()

        # Mock get_all to return None
        mock_queryset = mock.MagicMock()
        mock_queryset.filter.return_value.first.return_value = None
        mock_get_all.return_value = mock_queryset

        with self.assertRaises(MyValidationError) as context:
            self.app.force_stop_meeting(parent.id, "nonexistent_sub_id")

        self.assertEqual(context.exception.detail_code, RetCode.STATUS_PARAMETER_ERROR)


class MeetingAppSponsorsTest(TestCommonMeeting):
    """Test MeetingApp.get_meeting_sponsors method."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')
        self.app = MeetingApp()

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def test_get_meeting_sponsors_basic(self):
        """Test basic sponsor list retrieval."""
        MeetingDao.create(
            sponsor="Alice", group_name="group1", community=self.community,
            topic="Meeting 1", platform="WELINK", is_cycle=False,
            date=self.today, start="10:00", end="11:00", is_record=False,
            mid=f"mid1_{datetime.datetime.now().timestamp()}", host_id="h1@test.com"
        )
        MeetingDao.create(
            sponsor="Bob", group_name="group2", community=self.community,
            topic="Meeting 2", platform="WELINK", is_cycle=False,
            date=self.today, start="14:00", end="15:00", is_record=False,
            mid=f"mid2_{datetime.datetime.now().timestamp()}", host_id="h2@test.com"
        )

        result = self.app.get_meeting_sponsors(self.community)

        self.assertEqual(len(result), 2)
        self.assertIn("Alice", result)
        self.assertIn("Bob", result)

    def test_get_meeting_sponsors_with_keyword(self):
        """Test sponsor list with keyword filter."""
        MeetingDao.create(
            sponsor="Alice_Smith", group_name="group1", community=self.community,
            topic="Meeting 1", platform="WELINK", is_cycle=False,
            date=self.today, start="10:00", end="11:00", is_record=False,
            mid=f"mid1_{datetime.datetime.now().timestamp()}", host_id="h1@test.com"
        )
        MeetingDao.create(
            sponsor="Bob_Jones", group_name="group2", community=self.community,
            topic="Meeting 2", platform="WELINK", is_cycle=False,
            date=self.today, start="14:00", end="15:00", is_record=False,
            mid=f"mid2_{datetime.datetime.now().timestamp()}", host_id="h2@test.com"
        )

        result = self.app.get_meeting_sponsors(self.community, sponsor_keyword="Smith")

        self.assertEqual(len(result), 1)
        self.assertIn("Alice_Smith", result)


class MeetingAppMergedListTest(TestCommonMeeting):
    """Test MeetingApp.get_merged_meeting_list method."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')
        self.app = MeetingApp()

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def _create_non_cycle_meeting(self, **kwargs):
        """Create a non-cycle test meeting."""
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
            "is_delete": 0,
        }
        defaults.update(kwargs)
        return MeetingDao.create(**defaults)

    def _create_cycle_meeting_with_sub(self, **kwargs):
        """Create a cycle test meeting with sub meetings."""
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
            "is_delete": 0,
        }
        defaults.update(kwargs)
        parent = MeetingDao.create(**defaults)

        # Create cycle date
        MeetingCycleDao.create(
            mid=parent.mid,
            start_date=self.today,
            end_date=(datetime.datetime.now() + datetime.timedelta(days=7)).strftime('%Y-%m-%d'),
            start="10:00",
            end="11:00",
            cycle_type=CycleType.DAY.value,
            interval=1,
            meeting=parent
        )

        # Create sub meeting
        MeetingCycleSubMeetingDao.create(
            mid=parent.mid,
            sub_id=f"sub_{datetime.datetime.now().timestamp()}",
            date=self.today,
            start="10:00",
            end="11:00",
            meeting=parent,
            status=BusinessMeetingStatus.NOT_STARTED.value,
        )

        return parent

    def test_get_merged_meeting_list_pagination(self):
        """Test pagination in merged meeting list."""
        # Create multiple meetings
        for i in range(15):
            self._create_non_cycle_meeting(
                mid=f"mid_{i}_{datetime.datetime.now().timestamp()}",
                date=self.today
            )

        result = self.app.get_merged_meeting_list(
            community=self.community,
            filters={},
            page=1,
            page_size=10
        )

        self.assertEqual(result['page'], 1)
        self.assertEqual(result['size'], 10)
        self.assertEqual(len(result['list']), 10)
        self.assertEqual(result['total'], 15)

    def test_get_merged_meeting_list_filters(self):
        """Test filters in merged meeting list."""
        # Create meetings with different sponsors
        self._create_non_cycle_meeting(
            sponsor="Alice",
            mid=f"mid_a_{datetime.datetime.now().timestamp()}"
        )
        self._create_non_cycle_meeting(
            sponsor="Bob",
            mid=f"mid_b_{datetime.datetime.now().timestamp()}"
        )

        filters = {'sponsor': 'Alice'}
        result = self.app.get_merged_meeting_list(
            community=self.community,
            filters=filters,
            page=1,
            page_size=10
        )

        self.assertEqual(len(result['list']), 1)
        self.assertEqual(result['list'][0]['sponsor'], 'Alice')

    def test_get_merged_meeting_list_ordering(self):
        """Test ordering in merged meeting list."""
        # Create meetings with different dates
        yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        self._create_non_cycle_meeting(
            date=yesterday,
            mid=f"mid_y_{datetime.datetime.now().timestamp()}"
        )
        self._create_non_cycle_meeting(
            date=tomorrow,
            mid=f"mid_t_{datetime.datetime.now().timestamp()}"
        )

        # Test ascending order
        result = self.app.get_merged_meeting_list(
            community=self.community,
            filters={},
            order_by='date',
            order_type='asc',
            page=1,
            page_size=10
        )

        # First meeting should have yesterday's date
        first_date = result['list'][0]['date']
        if hasattr(first_date, 'strftime'):
            first_date = first_date.strftime('%Y-%m-%d')
        self.assertEqual(first_date, yesterday)

        # Test descending order
        result = self.app.get_merged_meeting_list(
            community=self.community,
            filters={},
            order_by='date',
            order_type='desc',
            page=1,
            page_size=10
        )

        # First meeting should have tomorrow's date
        first_date = result['list'][0]['date']
        if hasattr(first_date, 'strftime'):
            first_date = first_date.strftime('%Y-%m-%d')
        self.assertEqual(first_date, tomorrow)

    def test_get_merged_meeting_list_cycle_dates(self):
        """Test cycle meeting dates in merged meeting list."""
        parent = self._create_cycle_meeting_with_sub()

        result = self.app.get_merged_meeting_list(
            community=self.community,
            filters={},
            page=1,
            page_size=10
        )

        # Should include cycle meeting in results
        self.assertTrue(result['total'] >= 1)


class MeetingAppDeleteTest(TestCommonMeeting):
    """Test MeetingApp._delete_dao method."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')
        self.app = MeetingApp()

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def _create_cycle_meeting(self, **kwargs):
        """Create a cycle test meeting with sub meetings."""
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
        parent = MeetingDao.create(**defaults)

        # Create cycle date
        MeetingCycleDao.create(
            mid=parent.mid,
            start_date=self.today,
            end_date=(datetime.datetime.now() + datetime.timedelta(days=7)).strftime('%Y-%m-%d'),
            start="10:00",
            end="11:00",
            cycle_type=CycleType.DAY.value,
            interval=1,
            meeting=parent
        )

        # Create sub meeting
        MeetingCycleSubMeetingDao.create(
            mid=parent.mid,
            sub_id=f"sub_{datetime.datetime.now().timestamp()}",
            date=self.today,
            start="10:00",
            end="11:00",
            meeting=parent,
            status=BusinessMeetingStatus.NOT_STARTED.value,
        )

        return parent

    def test_delete_dao_cycle_meeting(self):
        """Test _delete_dao updates cycle sub meeting status."""
        parent = self._create_cycle_meeting()
        meeting_dict = model_to_dict(parent)
        meeting_dict['is_cycle'] = True
        meeting_dict['mid'] = parent.mid
        meeting_dict['sequence'] = 0

        result = self.app._delete_dao(parent.id, meeting_dict)

        self.assertEqual(result, parent.id)

        # Verify sub meeting status is updated
        sub_meetings = MeetingCycleSubMeetingDao.get_by_mid(parent.mid)
        for sub in sub_meetings:
            self.assertEqual(sub['status'], BusinessMeetingStatus.CANCELLED.value)


class MeetingAppThreadStartTest(TestCommonMeeting):
    """Test MeetingApp._send_message functionality."""

    def setUp(self):
        super().setUp()

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def test_send_message_calls_handlers(self):
        """Test _send_message calls message handlers."""
        app = MeetingApp()

        # Create mock meeting data
        meeting = {
            "community": "openEuler",
            "platform": "WELINK",
            "topic": "Test Meeting",
            "mid": "test_mid",
            "id": 1,
        }

        # Create mock handler class (returns mock instance)
        mock_instance = mock.MagicMock()
        mock_handler_class = mock.MagicMock(return_value=mock_instance)

        # Call _send_message
        app._send_message(meeting, [mock_handler_class])

        # Verify handler was instantiated and send_message was called
        mock_handler_class.assert_called_once()
        mock_instance.send_message.assert_called_once_with(meeting)