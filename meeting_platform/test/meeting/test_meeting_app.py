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

    @mock.patch('meeting.application.meeting.MeetingAdapterImpl.force_end_meeting')
    def test_force_stop_non_cycle_meeting_calls_clear_status(self, mock_force_end):
        """Test force_stop_meeting calls clear_status for non-cycle meeting (covers lines 616-617)."""
        mock_force_end.return_value = True
        meeting = self._create_non_cycle_meeting(status=BusinessMeetingStatus.ONGOING.value)

        result = self.app.force_stop_meeting(meeting.id, None)

        self.assertTrue(result)
        mock_force_end.assert_called_once()

        # Verify the meeting status was cleared (clear_status sets status to ENDED)
        updated_meeting = MeetingDao.get_by_id(meeting.id)
        self.assertEqual(updated_meeting.status, BusinessMeetingStatus.ENDED.value)

    @mock.patch('meeting.application.meeting.MeetingAdapterImpl.force_end_meeting')
    def test_force_stop_cycle_meeting_clears_ongoing_sub_meetings(self, mock_force_end):
        """Test force_stop_meeting for cycle meeting clears all ongoing sub meetings (covers lines 608-613)."""
        mock_force_end.return_value = True
        parent = self._create_cycle_meeting()
        # Create sub meetings with different statuses
        sub1 = self._create_sub_meeting(parent, status=BusinessMeetingStatus.ONGOING.value)
        sub2 = self._create_sub_meeting(parent, sub_id=f"sub2_{datetime.datetime.now().timestamp()}",
                                         status=BusinessMeetingStatus.NOT_STARTED.value)

        result = self.app.force_stop_meeting(parent.id, None)

        self.assertTrue(result)
        mock_force_end.assert_called_once()

        # Verify ongoing sub meeting status was cleared (set to ENDED)
        updated_sub1 = MeetingCycleSubMeetingDao.get_by_sub_id(sub1.sub_id)
        self.assertEqual(updated_sub1.status, BusinessMeetingStatus.ENDED.value)

        # Verify non-ongoing sub meeting status was NOT changed
        updated_sub2 = MeetingCycleSubMeetingDao.get_by_sub_id(sub2.sub_id)
        self.assertEqual(updated_sub2.status, BusinessMeetingStatus.NOT_STARTED.value)


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

    def test_get_merged_meeting_list_invalid_page(self):
        """Test get_merged_meeting_list corrects invalid page (covers lines 661-662)."""
        result = self.app.get_merged_meeting_list(
            community=self.community,
            filters={},
            page=-1,
            page_size=10
        )

        # Page should be corrected to 1
        self.assertEqual(result['page'], 1)

    def test_get_merged_meeting_list_invalid_page_size(self):
        """Test get_merged_meeting_list corrects invalid page_size (covers lines 663-664)."""
        result = self.app.get_merged_meeting_list(
            community=self.community,
            filters={},
            page=1,
            page_size=200  # Exceeds max 100
        )

        # Page size should be corrected to 10
        self.assertEqual(result['size'], 10)

    def test_get_merged_meeting_list_page_size_zero(self):
        """Test get_merged_meeting_list corrects zero page_size."""
        result = self.app.get_merged_meeting_list(
            community=self.community,
            filters={},
            page=1,
            page_size=0
        )

        # Page size should be corrected to 10
        self.assertEqual(result['size'], 10)

    def test_get_merged_meeting_list_invalid_order_by(self):
        """Test get_merged_meeting_list corrects invalid order_by (covers lines 666-668)."""
        result = self.app.get_merged_meeting_list(
            community=self.community,
            filters={},
            order_by='invalid_field',
            page=1,
            page_size=10
        )

        # Should still return results with default order_by
        self.assertIsNotNone(result['list'])

    def test_get_merged_meeting_list_order_type_desc(self):
        """Test get_merged_meeting_list with desc order_type (covers lines 684-685)."""
        self._create_non_cycle_meeting(mid=f"mid1_{datetime.datetime.now().timestamp()}")
        self._create_non_cycle_meeting(mid=f"mid2_{datetime.datetime.now().timestamp()}")

        result = self.app.get_merged_meeting_list(
            community=self.community,
            filters={},
            order_by='date',
            order_type='desc',
            page=1,
            page_size=10
        )

        self.assertIsNotNone(result['list'])

    def test_get_merged_meeting_list_order_type_asc(self):
        """Test get_merged_meeting_list with asc order_type."""
        self._create_non_cycle_meeting(mid=f"mid1_{datetime.datetime.now().timestamp()}")

        result = self.app.get_merged_meeting_list(
            community=self.community,
            filters={},
            order_by='date',
            order_type='asc',
            page=1,
            page_size=10
        )

        self.assertIsNotNone(result['list'])

    def test_get_merged_meeting_list_with_cycle_meetings(self):
        """Test get_merged_meeting_list includes cycle dates in response (covers lines 698-713)."""
        parent = self._create_cycle_meeting_with_sub()

        result = self.app.get_merged_meeting_list(
            community=self.community,
            filters={},
            page=1,
            page_size=10
        )

        # Should include cycle meeting data
        self.assertTrue(result['total'] >= 1)
        # Check if cycle dates are included in the list
        for meeting in result['list']:
            if meeting.get('is_cycle'):
                self.assertIsNotNone(meeting.get('cycle_start_date'))
                self.assertIsNotNone(meeting.get('cycle_end_date'))

    def test_get_merged_meeting_list_cycle_meetings_have_cycle_info(self):
        """Test cycle meetings have cycle_date info appended."""
        parent = self._create_cycle_meeting_with_sub()

        result = self.app.get_merged_meeting_list(
            community=self.community,
            filters={},
            page=1,
            page_size=10
        )

        # Find cycle meeting in results
        cycle_meetings = [m for m in result['list'] if m.get('is_cycle')]
        if cycle_meetings:
            # Cycle meeting should have cycle info
            for m in cycle_meetings:
                self.assertIn('cycle_start_date', m)
                self.assertIn('cycle_end_date', m)

    def test_get_merged_meeting_list_sort_by_topic_same_start(self):
        """Test meetings with same start time are sorted by topic alphabetically."""
        self._create_non_cycle_meeting(
            topic="Beta Meeting",
            start="10:00",
            mid=f"mid1_{datetime.datetime.now().timestamp()}"
        )
        self._create_non_cycle_meeting(
            topic="Alpha Meeting",
            start="10:00",
            mid=f"mid2_{datetime.datetime.now().timestamp()}"
        )
        self._create_non_cycle_meeting(
            topic="Gamma Meeting",
            start="10:00",
            mid=f"mid3_{datetime.datetime.now().timestamp()}"
        )

        result = self.app.get_merged_meeting_list(
            community=self.community,
            filters={},
            order_by='date',
            order_type='asc',
            page=1,
            page_size=10
        )

        self.assertEqual(result['total'], 3)
        meeting_topics = [m['topic'] for m in result['list']]
        self.assertEqual(meeting_topics, ["Alpha Meeting", "Beta Meeting", "Gamma Meeting"])

    def test_get_merged_meeting_list_sort_priority(self):
        """Test sorting priority: date → start → topic."""
        yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        self._create_non_cycle_meeting(
            topic="Z Meeting",
            date=yesterday,
            start="10:00",
            mid=f"mid_y1_{datetime.datetime.now().timestamp()}"
        )
        self._create_non_cycle_meeting(
            topic="A Meeting",
            date=yesterday,
            start="14:00",
            mid=f"mid_y2_{datetime.datetime.now().timestamp()}"
        )
        self._create_non_cycle_meeting(
            topic="B Meeting",
            date=self.today,
            start="10:00",
            mid=f"mid_t1_{datetime.datetime.now().timestamp()}"
        )
        self._create_non_cycle_meeting(
            topic="C Meeting",
            date=self.today,
            start="10:00",
            mid=f"mid_t2_{datetime.datetime.now().timestamp()}"
        )
        self._create_non_cycle_meeting(
            topic="A Meeting",
            date=self.today,
            start="10:00",
            mid=f"mid_t3_{datetime.datetime.now().timestamp()}"
        )

        result = self.app.get_merged_meeting_list(
            community=self.community,
            filters={},
            order_by='date',
            order_type='asc',
            page=1,
            page_size=10
        )

        self.assertEqual(result['total'], 5)
        meeting_list = result['list']
        first_date = meeting_list[0]['date']
        if hasattr(first_date, 'strftime'):
            first_date = first_date.strftime('%Y-%m-%d')
        self.assertEqual(first_date, yesterday)
        second_date = meeting_list[1]['date']
        if hasattr(second_date, 'strftime'):
            second_date = second_date.strftime('%Y-%m-%d')
        self.assertEqual(second_date, yesterday)
        self.assertEqual(meeting_list[0]['start'], "10:00")
        self.assertEqual(meeting_list[1]['start'], "14:00")
        third_date = meeting_list[2]['date']
        if hasattr(third_date, 'strftime'):
            third_date = third_date.strftime('%Y-%m-%d')
        self.assertEqual(third_date, self.today)
        same_start_topics = [m['topic'] for m in meeting_list if m['date'].strftime('%Y-%m-%d') == self.today and m['start'] == "10:00"]
        self.assertEqual(same_start_topics, ["A Meeting", "B Meeting", "C Meeting"])

    def test_get_merged_meeting_list_topic_sort_with_desc(self):
        """Test topic sorts ascending even when order_type is desc."""
        yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        self._create_non_cycle_meeting(
            topic="C Meeting",
            date=self.today,
            start="10:00",
            mid=f"mid1_{datetime.datetime.now().timestamp()}"
        )
        self._create_non_cycle_meeting(
            topic="A Meeting",
            date=self.today,
            start="10:00",
            mid=f"mid2_{datetime.datetime.now().timestamp()}"
        )
        self._create_non_cycle_meeting(
            topic="B Meeting",
            date=self.today,
            start="10:00",
            mid=f"mid3_{datetime.datetime.now().timestamp()}"
        )

        result = self.app.get_merged_meeting_list(
            community=self.community,
            filters={},
            order_by='date',
            order_type='desc',
            page=1,
            page_size=10
        )

        self.assertEqual(result['total'], 3)
        same_start_topics = [m['topic'] for m in result['list'] if m['start'] == "10:00"]
        self.assertEqual(same_start_topics, ["A Meeting", "B Meeting", "C Meeting"])


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


class MeetingAppGetMeetingSponsorsTest(TestCommonMeeting):
    """Test MeetingApp.get_meeting_sponsors method (covers lines 572, 582-583)."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')
        self.app = MeetingApp()

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def test_get_meeting_sponsors_returns_list(self):
        """Test get_meeting_sponsors returns list (covers lines 572, 582-583)."""
        MeetingDao.create(
            sponsor="Alice", group_name="group1", community=self.community,
            topic="Meeting 1", platform="WELINK", is_cycle=False,
            date=self.today, start="10:00", end="11:00", is_record=False,
            mid=f"mid1_{datetime.datetime.now().timestamp()}", host_id="h1@test.com"
        )

        result = self.app.get_meeting_sponsors(self.community)

        self.assertIsInstance(result, list)
        self.assertIn("Alice", result)

    def test_get_meeting_sponsors_with_keyword_returns_list(self):
        """Test get_meeting_sponsors with keyword returns list."""
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

        self.assertIsInstance(result, list)
        self.assertIn("Alice_Smith", result)


class MeetingAppForceStopMeetingFullTest(TestCommonMeeting):
    """Test MeetingApp.force_stop_meeting method covering all branches."""

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
    def test_force_stop_non_cycle_calls_dao_clear_status(self, mock_force_end):
        """Test force_stop_meeting calls meeting_dao.clear_status for non-cycle (covers lines 616-617)."""
        mock_force_end.return_value = True
        meeting = self._create_non_cycle_meeting(status=BusinessMeetingStatus.ONGOING.value)

        result = self.app.force_stop_meeting(meeting.id, None)

        self.assertTrue(result)
        # Verify meeting status was cleared
        updated = MeetingDao.get_by_id(meeting.id)
        self.assertEqual(updated.status, BusinessMeetingStatus.ENDED.value)

    @mock.patch('meeting.application.meeting.MeetingAdapterImpl.force_end_meeting')
    def test_force_stop_cycle_clears_ongoing_sub_meetings(self, mock_force_end):
        """Test force_stop_meeting clears ongoing sub meetings for cycle meeting (covers lines 608-613)."""
        mock_force_end.return_value = True
        parent = self._create_cycle_meeting()
        sub_ongoing = self._create_sub_meeting(parent, status=BusinessMeetingStatus.ONGOING.value)
        sub_not_started = self._create_sub_meeting(
            parent, sub_id=f"sub2_{datetime.datetime.now().timestamp()}",
            status=BusinessMeetingStatus.NOT_STARTED.value
        )

        result = self.app.force_stop_meeting(parent.id, None)

        self.assertTrue(result)
        # Verify ongoing sub meeting was cleared
        updated_ongoing = MeetingCycleSubMeetingDao.get_by_sub_id(sub_ongoing.sub_id)
        self.assertEqual(updated_ongoing.status, BusinessMeetingStatus.ENDED.value)
        # Verify non-ongoing sub meeting was NOT changed
        updated_not_started = MeetingCycleSubMeetingDao.get_by_sub_id(sub_not_started.sub_id)
        self.assertEqual(updated_not_started.status, BusinessMeetingStatus.NOT_STARTED.value)

    @mock.patch('meeting.application.meeting.MeetingAdapterImpl.force_end_meeting')
    @mock.patch('meeting.infrastructure.dao.meeting_cycle_sub_dao.MeetingCycleSubMeetingDao.clear_status')
    def test_force_stop_cycle_with_sub_id_calls_clear_status(self, mock_clear_status, mock_force_end):
        """Test force_stop_meeting with sub_id calls clear_status (covers line 603)."""
        mock_force_end.return_value = True
        parent = self._create_cycle_meeting()
        sub = self._create_sub_meeting(parent)

        result = self.app.force_stop_meeting(parent.id, sub.sub_id)

        self.assertTrue(result)
        mock_clear_status.assert_called_once_with(sub.sub_id)

    def test_force_stop_meeting_not_found_raises_error(self):
        """Test force_stop_meeting raises error for nonexistent meeting (covers lines 586-589)."""
        with self.assertRaises(MyValidationError) as context:
            self.app.force_stop_meeting(99999, None)

        self.assertEqual(context.exception.detail_code, RetCode.STATUS_PARAMETER_ERROR)

    @mock.patch('meeting.infrastructure.dao.meeting_cycle_sub_dao.MeetingCycleSubMeetingDao.get_all')
    def test_force_stop_sub_meeting_not_found_raises_error(self, mock_get_all):
        """Test force_stop_meeting raises error for nonexistent sub meeting (covers lines 595-597)."""
        parent = self._create_cycle_meeting()

        mock_queryset = mock.MagicMock()
        mock_queryset.filter.return_value.first.return_value = None
        mock_get_all.return_value = mock_queryset

        with self.assertRaises(MyValidationError) as context:
            self.app.force_stop_meeting(parent.id, "nonexistent_sub_id")

        self.assertEqual(context.exception.detail_code, RetCode.STATUS_PARAMETER_ERROR)