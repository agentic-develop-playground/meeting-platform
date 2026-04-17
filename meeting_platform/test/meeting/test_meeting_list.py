#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
"""
Unit tests for meeting list API functionality.

Tests include:
- MeetingListView.get endpoint tests
- MeetingApp.get_merged_meeting_list application layer tests
- Filtering, pagination, and sorting functionality
- Cycle meeting list expansion and cycle info inclusion
"""
import datetime
import logging
from datetime import timedelta

from rest_framework import status

from meeting.infrastructure.dao.meeting_dao import MeetingDao
from meeting.infrastructure.dao.meeting_cycle_dao import MeetingCycleDao
from meeting.infrastructure.dao.meeting_cycle_sub_dao import MeetingCycleSubMeetingDao
from meeting.domain.primitive.meeting_status import BusinessMeetingStatus
from meeting_platform.test.meeting.test_base import TestCommonMeeting

logger = logging.getLogger("log")


class MeetingListViewTest(TestCommonMeeting):
    """Test MeetingListView.get endpoint for merged meeting list."""

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

    def _create_cycle_date(self, parent_meeting, **kwargs):
        """Create cycle date record for a cycle meeting."""
        defaults = {
            "mid": parent_meeting.mid,
            "start_date": "2026-04-01",
            "end_date": "2026-04-30",
            "start": "10:00",
            "end": "11:00",
            "cycle_type": 1,  # Daily cycle
            "interval": 1,
            "meeting": parent_meeting,
        }
        defaults.update(kwargs)
        return MeetingCycleDao.create(**defaults)

    def test_meeting_list_basic(self):
        """Test basic meeting list query returns correct results."""
        meeting = self._create_test_meeting(topic="Basic Test Meeting")

        response = self.client.get(f"{self.url}?community={self.community}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json() if hasattr(response, 'json') else response.data

        self.assertIn('data', data)
        self.assertIn('list', data['data'])
        self.assertIn('total', data['data'])
        self.assertGreaterEqual(data['data']['total'], 1)

        # Verify meeting data is correct
        meeting_data = data['data']['list'][0]
        self.assertEqual(meeting_data['topic'], "Basic Test Meeting")
        self.assertEqual(meeting_data['sponsor'], "test_sponsor")
        self.assertEqual(meeting_data['community'], self.community)
        self.assertFalse(meeting_data['is_cycle'])

    def test_meeting_list_includes_cycle_sub_meetings(self):
        """Test that meeting list includes cycle sub-meetings."""
        # Create a regular meeting
        regular_meeting = self._create_test_meeting(
            topic="Regular Meeting",
            mid=f"regular_mid_{datetime.datetime.now().timestamp()}"
        )

        # Create a cycle meeting with sub meetings
        parent = self._create_parent_meeting()
        sub1 = self._create_sub_meeting(parent, date=self.today)
        sub2 = self._create_sub_meeting(
            parent,
            sub_id=f"sub2_{datetime.datetime.now().timestamp()}",
            date=(datetime.datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        )

        response = self.client.get(f"{self.url}?community={self.community}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json() if hasattr(response, 'json') else response.data

        # Should include both regular meeting and cycle sub meetings
        self.assertGreaterEqual(data['data']['total'], 3)

        # Verify cycle sub meetings are marked as is_cycle=True
        cycle_meetings = [m for m in data['data']['list'] if m.get('is_cycle')]
        self.assertGreaterEqual(len(cycle_meetings), 2)

        # Each cycle sub meeting should have a sub_id
        for cycle_m in cycle_meetings:
            self.assertIsNotNone(cycle_m.get('sub_id'))

    def test_meeting_list_with_date_filter(self):
        """Test meeting list with date range filtering."""
        yesterday = (datetime.datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow = (datetime.datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        # Create meetings on different dates
        meeting_yesterday = self._create_test_meeting(
            date=yesterday,
            topic="Yesterday Meeting",
            mid=f"yesterday_mid_{datetime.datetime.now().timestamp()}"
        )
        meeting_today = self._create_test_meeting(topic="Today Meeting")
        meeting_tomorrow = self._create_test_meeting(
            date=tomorrow,
            topic="Tomorrow Meeting",
            mid=f"tomorrow_mid_{datetime.datetime.now().timestamp()}"
        )

        # Filter by single date
        response = self.client.get(f"{self.url}?community={self.community}&date={self.today}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json() if hasattr(response, 'json') else response.data

        # Should only return today's meeting
        self.assertEqual(data['data']['total'], 1)
        self.assertEqual(data['data']['list'][0]['topic'], "Today Meeting")

        # Filter by date range
        response = self.client.get(
            f"{self.url}?community={self.community}&start_date={yesterday}&end_date={self.today}"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json() if hasattr(response, 'json') else response.data

        # Should return yesterday and today meetings
        self.assertGreaterEqual(data['data']['total'], 2)
        topics = [m['topic'] for m in data['data']['list']]
        self.assertIn("Yesterday Meeting", topics)
        self.assertIn("Today Meeting", topics)

    def test_meeting_list_with_sponsor_filter(self):
        """Test meeting list with sponsor filtering."""
        meeting1 = self._create_test_meeting(sponsor="Alice")
        meeting2 = self._create_test_meeting(
            sponsor="Bob",
            mid=f"mid2_{datetime.datetime.now().timestamp()}"
        )
        meeting3 = self._create_test_meeting(
            sponsor="Charlie",
            mid=f"mid3_{datetime.datetime.now().timestamp()}"
        )

        response = self.client.get(f"{self.url}?community={self.community}&sponsor=Alice")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json() if hasattr(response, 'json') else response.data

        # Should only return Alice's meetings
        self.assertGreaterEqual(data['data']['total'], 1)
        for m in data['data']['list']:
            self.assertEqual(m['sponsor'], "Alice")

    def test_meeting_list_with_status_filter(self):
        """Test meeting list with status filtering."""
        # Create meetings with different statuses
        meeting_not_started = self._create_test_meeting(
            status=BusinessMeetingStatus.NOT_STARTED.value,
            topic="Not Started Meeting"
        )
        meeting_ongoing = self._create_test_meeting(
            status=BusinessMeetingStatus.ONGOING.value,
            topic="Ongoing Meeting",
            mid=f"ongoing_mid_{datetime.datetime.now().timestamp()}"
        )
        meeting_ended = self._create_test_meeting(
            status=BusinessMeetingStatus.ENDED.value,
            topic="Ended Meeting",
            mid=f"ended_mid_{datetime.datetime.now().timestamp()}"
        )

        # Filter by status=1 (ongoing)
        response = self.client.get(f"{self.url}?community={self.community}&status=1")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json() if hasattr(response, 'json') else response.data

        # Should only return ongoing meeting
        self.assertGreaterEqual(data['data']['total'], 1)
        topics = [m['topic'] for m in data['data']['list']]
        self.assertIn("Ongoing Meeting", topics)

    def test_meeting_list_pagination(self):
        """Test meeting list pagination functionality."""
        # Create multiple meetings
        for i in range(15):
            self._create_test_meeting(
                topic=f"Meeting {i}",
                mid=f"mid_pagination_{i}_{datetime.datetime.now().timestamp()}"
            )

        # Test first page
        response = self.client.get(f"{self.url}?community={self.community}&page=1&size=5")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json() if hasattr(response, 'json') else response.data

        self.assertEqual(len(data['data']['list']), 5)
        self.assertEqual(data['data']['page'], 1)
        self.assertEqual(data['data']['size'], 5)

        # Test second page
        response = self.client.get(f"{self.url}?community={self.community}&page=2&size=5")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json() if hasattr(response, 'json') else response.data

        self.assertEqual(len(data['data']['list']), 5)
        self.assertEqual(data['data']['page'], 2)

        # Test page size limit (max 100)
        response = self.client.get(f"{self.url}?community={self.community}&page=1&size=150")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_meeting_list_order_by_date_asc(self):
        """Test meeting list ascending date sort."""
        yesterday = (datetime.datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow = (datetime.datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        # Create meetings on different dates
        meeting1 = self._create_test_meeting(
            date=tomorrow,
            mid=f"mid_asc1_{datetime.datetime.now().timestamp()}"
        )
        meeting2 = self._create_test_meeting(
            date=yesterday,
            mid=f"mid_asc2_{datetime.datetime.now().timestamp()}"
        )
        meeting3 = self._create_test_meeting(
            date=self.today,
            mid=f"mid_asc3_{datetime.datetime.now().timestamp()}"
        )

        response = self.client.get(
            f"{self.url}?community={self.community}&order_by=date&order_type=asc"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json() if hasattr(response, 'json') else response.data

        # Verify dates are in ascending order
        dates = [m['date'] for m in data['data']['list']]
        sorted_dates = sorted(dates)
        self.assertEqual(dates, sorted_dates)

    def test_meeting_list_order_by_date_desc(self):
        """Test meeting list descending date sort."""
        yesterday = (datetime.datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow = (datetime.datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        # Create meetings on different dates
        meeting1 = self._create_test_meeting(
            date=yesterday,
            mid=f"mid_desc1_{datetime.datetime.now().timestamp()}"
        )
        meeting2 = self._create_test_meeting(
            date=tomorrow,
            mid=f"mid_desc2_{datetime.datetime.now().timestamp()}"
        )
        meeting3 = self._create_test_meeting(
            date=self.today,
            mid=f"mid_desc3_{datetime.datetime.now().timestamp()}"
        )

        response = self.client.get(
            f"{self.url}?community={self.community}&order_by=date&order_type=desc"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json() if hasattr(response, 'json') else response.data

        # Verify dates are in descending order
        dates = [m['date'] for m in data['data']['list']]
        sorted_dates_desc = sorted(dates, reverse=True)
        self.assertEqual(dates, sorted_dates_desc)

    def test_meeting_list_invalid_community(self):
        """Test that invalid community returns 400 error."""
        response = self.client.get(f"{self.url}?community=invalid_community_name")

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_meeting_list_cycle_meeting_includes_cycle_dates(self):
        """Test that cycle meeting in list includes cycle info."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent)

        # Create cycle date record
        cycle_date = self._create_cycle_date(
            parent,
            start_date="2026-04-01",
            end_date="2026-04-30",
            start="14:00",
            end="15:00",
            cycle_type=2,  # Weekly cycle
            interval=1
        )

        response = self.client.get(f"{self.url}?community={self.community}")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json() if hasattr(response, 'json') else response.data

        # Find the cycle meeting in results
        cycle_meetings = [m for m in data['data']['list'] if m.get('is_cycle')]
        self.assertGreaterEqual(len(cycle_meetings), 1)

        cycle_meeting = cycle_meetings[0]

        # Verify cycle info fields are present
        self.assertIn('cycle_start_date', cycle_meeting)
        self.assertIn('cycle_end_date', cycle_meeting)
        self.assertIn('cycle_start', cycle_meeting)
        self.assertIn('cycle_end', cycle_meeting)
        self.assertIn('cycle_type', cycle_meeting)
        self.assertIn('cycle_interval', cycle_meeting)

        # Verify cycle info values match the cycle_date record
        self.assertEqual(cycle_meeting['cycle_start_date'], "2026-04-01")
        self.assertEqual(cycle_meeting['cycle_end_date'], "2026-04-30")
        self.assertEqual(cycle_meeting['cycle_start'], "14:00")
        self.assertEqual(cycle_meeting['cycle_end'], "15:00")
        self.assertEqual(cycle_meeting['cycle_type'], 2)
        self.assertEqual(cycle_meeting['cycle_interval'], 1)


class MeetingAppMergedMeetingListTest(TestCommonMeeting):
    """Test MeetingApp.get_merged_meeting_list application method."""

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

    def _create_cycle_date(self, parent_meeting, **kwargs):
        """Create cycle date record for a cycle meeting."""
        defaults = {
            "mid": parent_meeting.mid,
            "start_date": "2026-04-01",
            "end_date": "2026-04-30",
            "start": "10:00",
            "end": "11:00",
            "cycle_type": 1,
            "interval": 1,
            "meeting": parent_meeting,
        }
        defaults.update(kwargs)
        return MeetingCycleDao.create(**defaults)

    def test_get_merged_meeting_list_basic(self):
        """Test basic merged meeting list retrieval."""
        from meeting.application.meeting import MeetingApp

        meeting = self._create_test_meeting()

        app = MeetingApp()
        result = app.get_merged_meeting_list(self.community, {})

        self.assertIn('total', result)
        self.assertIn('list', result)
        self.assertIn('page', result)
        self.assertIn('size', result)
        self.assertGreaterEqual(result['total'], 1)

    def test_get_merged_meeting_list_includes_cycle_sub_meetings(self):
        """Test that merged list includes expanded cycle sub meetings."""
        from meeting.application.meeting import MeetingApp

        # Create regular meeting
        regular = self._create_test_meeting(
            mid=f"regular_mid_{datetime.datetime.now().timestamp()}"
        )

        # Create cycle meeting with sub meetings
        parent = self._create_parent_meeting()
        sub1 = self._create_sub_meeting(parent)
        sub2 = self._create_sub_meeting(
            parent,
            sub_id=f"sub2_{datetime.datetime.now().timestamp()}",
            date=(datetime.datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        )

        app = MeetingApp()
        result = app.get_merged_meeting_list(self.community, {})

        # Should include all meetings
        self.assertGreaterEqual(result['total'], 3)

        # Verify sub meetings have is_cycle=True and sub_id
        cycle_items = [m for m in result['list'] if m.get('is_cycle')]
        self.assertGreaterEqual(len(cycle_items), 2)

    def test_get_merged_meeting_list_pagination(self):
        """Test merged meeting list pagination parameters."""
        from meeting.application.meeting import MeetingApp

        # Create multiple meetings
        for i in range(5):
            self._create_test_meeting(
                mid=f"mid_page_{i}_{datetime.datetime.now().timestamp()}"
            )

        app = MeetingApp()

        # Test page correction (page < 1 becomes 1)
        result = app.get_merged_meeting_list(self.community, {}, page=0)
        self.assertEqual(result['page'], 1)

        # Test page size correction (page_size > 100 becomes 10)
        result = app.get_merged_meeting_list(self.community, {}, page_size=150)
        self.assertEqual(result['size'], 10)

        # Test page size correction (page_size < 1 becomes 10)
        result = app.get_merged_meeting_list(self.community, {}, page_size=0)
        self.assertEqual(result['size'], 10)

    def test_get_merged_meeting_list_sorting(self):
        """Test merged meeting list sorting parameters."""
        from meeting.application.meeting import MeetingApp

        yesterday = (datetime.datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow = (datetime.datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        # Create meetings on different dates
        self._create_test_meeting(
            date=yesterday,
            mid=f"mid_sort1_{datetime.datetime.now().timestamp()}"
        )
        self._create_test_meeting(
            date=tomorrow,
            mid=f"mid_sort2_{datetime.datetime.now().timestamp()}"
        )
        self._create_test_meeting(
            date=self.today,
            mid=f"mid_sort3_{datetime.datetime.now().timestamp()}"
        )

        app = MeetingApp()

        # Test ascending sort
        result = app.get_merged_meeting_list(
            self.community, {}, order_by='date', order_type='asc'
        )
        dates = [m['date'] for m in result['list']]
        self.assertEqual(dates, sorted(dates))

        # Test descending sort
        result = app.get_merged_meeting_list(
            self.community, {}, order_by='date', order_type='desc'
        )
        dates = [m['date'] for m in result['list']]
        self.assertEqual(dates, sorted(dates, reverse=True))

        # Test invalid order_by defaults to 'date'
        result = app.get_merged_meeting_list(
            self.community, {}, order_by='invalid_field'
        )
        self.assertIn('list', result)

    def test_get_merged_meeting_list_filter_by_date(self):
        """Test merged meeting list date filtering."""
        from meeting.application.meeting import MeetingApp

        yesterday = (datetime.datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow = (datetime.datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

        # Create meetings on different dates
        self._create_test_meeting(
            date=yesterday,
            mid=f"mid_date1_{datetime.datetime.now().timestamp()}"
        )
        self._create_test_meeting(
            date=self.today,
            mid=f"mid_date2_{datetime.datetime.now().timestamp()}"
        )
        self._create_test_meeting(
            date=tomorrow,
            mid=f"mid_date3_{datetime.datetime.now().timestamp()}"
        )

        app = MeetingApp()

        # Filter by single date
        result = app.get_merged_meeting_list(
            self.community, {'date': self.today}
        )

        # Should only return today's meetings
        for m in result['list']:
            self.assertEqual(m['date'], self.today)

    def test_get_merged_meeting_list_filter_by_sponsor(self):
        """Test merged meeting list sponsor filtering."""
        from meeting.application.meeting import MeetingApp

        meeting1 = self._create_test_meeting(sponsor="Alice")
        meeting2 = self._create_test_meeting(
            sponsor="Bob",
            mid=f"mid_sponsor_{datetime.datetime.now().timestamp()}"
        )

        app = MeetingApp()

        result = app.get_merged_meeting_list(
            self.community, {'sponsor': 'Alice'}
        )

        # Should only return Alice's meetings
        for m in result['list']:
            self.assertEqual(m['sponsor'], 'Alice')

    def test_get_merged_meeting_list_filter_by_status(self):
        """Test merged meeting list status filtering."""
        from meeting.application.meeting import MeetingApp

        meeting1 = self._create_test_meeting(
            status=BusinessMeetingStatus.NOT_STARTED.value
        )
        meeting2 = self._create_test_meeting(
            status=BusinessMeetingStatus.ONGOING.value,
            mid=f"mid_status_{datetime.datetime.now().timestamp()}"
        )

        app = MeetingApp()

        result = app.get_merged_meeting_list(
            self.community, {'status': BusinessMeetingStatus.ONGOING.value}
        )

        # Should only return ongoing meetings
        for m in result['list']:
            # Status in expanded list comes from database status
            self.assertEqual(m.get('status'), BusinessMeetingStatus.ONGOING.value)

    def test_get_merged_meeting_list_cycle_info(self):
        """Test merged meeting list includes cycle info for cycle meetings."""
        from meeting.application.meeting import MeetingApp

        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent)

        # Create cycle date record with specific values
        cycle_date = self._create_cycle_date(
            parent,
            start_date="2026-01-01",
            end_date="2026-12-31",
            start="09:00",
            end="10:00",
            cycle_type=2,  # Weekly
            interval=7,
            point="1,3,5"  # Mon, Wed, Fri
        )

        app = MeetingApp()
        result = app.get_merged_meeting_list(self.community, {})

        # Find the cycle meeting
        cycle_meetings = [m for m in result['list'] if m.get('is_cycle')]
        self.assertGreaterEqual(len(cycle_meetings), 1)

        cycle_meeting = cycle_meetings[0]

        # Verify cycle info fields
        self.assertEqual(cycle_meeting['cycle_start_date'], "2026-01-01")
        self.assertEqual(cycle_meeting['cycle_end_date'], "2026-12-31")
        self.assertEqual(cycle_meeting['cycle_start'], "09:00")
        self.assertEqual(cycle_meeting['cycle_end'], "10:00")
        self.assertEqual(cycle_meeting['cycle_type'], 2)
        self.assertEqual(cycle_meeting['cycle_interval'], 7)
        # cycle_point is a list split from comma-separated string
        self.assertIn('cycle_point', cycle_meeting)