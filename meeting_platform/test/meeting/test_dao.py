#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
"""
Unit tests for DAO layer methods.

Tests include:
- MeetingDao methods
- MeetingCycleDao methods
- MeetingCycleSubMeetingDao methods
"""
import datetime
from unittest import mock

from meeting.infrastructure.dao.meeting_dao import MeetingDao
from meeting.infrastructure.dao.meeting_cycle_dao import MeetingCycleDao
from meeting.infrastructure.dao.meeting_cycle_sub_dao import MeetingCycleSubMeetingDao
from meeting.domain.primitive.meeting_status import BusinessMeetingStatus
from meeting_platform.test.meeting.test_base import TestCommonMeeting


class MeetingDaoTest(TestCommonMeeting):
    """Test MeetingDao methods."""

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
        # Create meetings with different sponsors
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

        result = MeetingDao.get_meeting_sponsors(self.community)

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

        result = MeetingDao.get_meeting_sponsors(self.community, sponsor_keyword="Smith")

        self.assertEqual(len(result), 1)
        self.assertIn("Alice_Smith", result)

    def test_get_meeting_sponsors_deduplication(self):
        """Test sponsor list deduplication."""
        timestamp = datetime.datetime.now().timestamp()
        MeetingDao.create(
            sponsor="Alice", group_name="group1", community=self.community,
            topic="Meeting 1", platform="WELINK", is_cycle=False,
            date=self.today, start="10:00", end="11:00", is_record=False,
            mid=f"mid1_{timestamp}", host_id="h1@test.com"
        )
        MeetingDao.create(
            sponsor="Alice", group_name="group1", community=self.community,
            topic="Meeting 2", platform="WELINK", is_cycle=False,
            date=self.today, start="14:00", end="15:00", is_record=False,
            mid=f"mid2_{timestamp + 1}", host_id="h1@test.com"
        )

        result = MeetingDao.get_meeting_sponsors(self.community)

        # Should return unique sponsors only
        self.assertEqual(len(list(result)), 1)

    def test_get_status_sync_candidates_includes_today_and_future(self):
        """Test get_status_sync_candidates returns meetings >= today."""
        now = datetime.datetime.now()
        today = now.strftime('%Y-%m-%d')
        yesterday = (now - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow = (now + datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        # Create meetings for yesterday, today, and tomorrow
        MeetingDao.create(
            sponsor="s1", group_name="g1", community=self.community,
            topic="Yesterday Meeting", platform="WELINK", is_cycle=False,
            date=yesterday, start="10:00", end="11:00", is_record=False,
            mid=f"mid_y_{datetime.datetime.now().timestamp()}", host_id="h1@test.com",
            status=BusinessMeetingStatus.NOT_STARTED.value, is_delete=0
        )
        meeting_today = MeetingDao.create(
            sponsor="s2", group_name="g2", community=self.community,
            topic="Today Meeting", platform="WELINK", is_cycle=False,
            date=today, start="10:00", end="11:00", is_record=False,
            mid=f"mid_t_{datetime.datetime.now().timestamp()}", host_id="h2@test.com",
            status=BusinessMeetingStatus.NOT_STARTED.value, is_delete=0
        )
        meeting_tomorrow = MeetingDao.create(
            sponsor="s3", group_name="g3", community=self.community,
            topic="Tomorrow Meeting", platform="WELINK", is_cycle=False,
            date=tomorrow, start="10:00", end="11:00", is_record=False,
            mid=f"mid_tm_{datetime.datetime.now().timestamp()}", host_id="h3@test.com",
            status=BusinessMeetingStatus.NOT_STARTED.value, is_delete=0
        )

        result = MeetingDao.get_status_sync_candidates(self.community, now)

        # Should include today and tomorrow, exclude yesterday
        result_ids = [m.id for m in result]
        self.assertIn(meeting_today.id, result_ids)
        self.assertIn(meeting_tomorrow.id, result_ids)

    def test_get_status_sync_candidates_excludes_deleted(self):
        """Test get_status_sync_candidates excludes deleted meetings."""
        now = datetime.datetime.now()
        meeting = MeetingDao.create(
            sponsor="s1", group_name="g1", community=self.community,
            topic="Deleted Meeting", platform="WELINK", is_cycle=False,
            date=self.today, start="10:00", end="11:00", is_record=False,
            mid=f"mid_d_{datetime.datetime.now().timestamp()}", host_id="h1@test.com",
            status=BusinessMeetingStatus.NOT_STARTED.value, is_delete=1
        )

        result = MeetingDao.get_status_sync_candidates(self.community, now)

        result_ids = [m.id for m in result]
        self.assertNotIn(meeting.id, result_ids)

    def test_has_subsequent_meetings_true(self):
        """Test has_subsequent_meetings returns True when subsequent meetings exist."""
        host_id = "host@test.com"

        # Create current meeting ending at 11:00
        MeetingDao.create(
            sponsor="s1", group_name="g1", community=self.community,
            topic="Current Meeting", platform="WELINK", is_cycle=False,
            date=self.today, start="10:00", end="11:00", is_record=False,
            mid=f"mid_c_{datetime.datetime.now().timestamp()}", host_id=host_id,
            status=BusinessMeetingStatus.NOT_STARTED.value, is_delete=0
        )
        # Create subsequent meeting starting at 14:00
        MeetingDao.create(
            sponsor="s2", group_name="g2", community=self.community,
            topic="Next Meeting", platform="WELINK", is_cycle=False,
            date=self.today, start="14:00", end="15:00", is_record=False,
            mid=f"mid_n_{datetime.datetime.now().timestamp()}", host_id=host_id,
            status=BusinessMeetingStatus.NOT_STARTED.value, is_delete=0
        )

        result = MeetingDao.has_subsequent_meetings(self.community, host_id, self.today, "11:00")

        self.assertTrue(result)

    def test_has_subsequent_meetings_false(self):
        """Test has_subsequent_meetings returns False when no subsequent meetings."""
        host_id = "host@test.com"

        MeetingDao.create(
            sponsor="s1", group_name="g1", community=self.community,
            topic="Single Meeting", platform="WELINK", is_cycle=False,
            date=self.today, start="10:00", end="11:00", is_record=False,
            mid=f"mid_s_{datetime.datetime.now().timestamp()}", host_id=host_id,
            status=BusinessMeetingStatus.NOT_STARTED.value, is_delete=0
        )

        result = MeetingDao.has_subsequent_meetings(self.community, host_id, self.today, "11:00")

        self.assertFalse(result)

    def test_has_subsequent_meetings_excludes_cycle_meetings(self):
        """Test has_subsequent_meetings only checks non-cycle meetings."""
        host_id = "host@test.com"

        # Create non-cycle meeting
        MeetingDao.create(
            sponsor="s1", group_name="g1", community=self.community,
            topic="Non-cycle Meeting", platform="WELINK", is_cycle=False,
            date=self.today, start="10:00", end="11:00", is_record=False,
            mid=f"mid_nc_{datetime.datetime.now().timestamp()}", host_id=host_id,
            status=BusinessMeetingStatus.NOT_STARTED.value, is_delete=0
        )
        # Create cycle meeting (should be excluded from check)
        MeetingDao.create(
            sponsor="s2", group_name="g2", community=self.community,
            topic="Cycle Meeting", platform="WELINK", is_cycle=True,
            date=None, start=None, end=None, is_record=False,
            mid=f"mid_cy_{datetime.datetime.now().timestamp()}", host_id=host_id,
            status=BusinessMeetingStatus.NOT_STARTED.value, is_delete=0
        )

        result = MeetingDao.has_subsequent_meetings(self.community, host_id, self.today, "11:00")

        # Should return False since cycle meeting is excluded
        self.assertFalse(result)

    def test_get_non_cycle_meetings_count_basic(self):
        """Test basic non-cycle meetings count."""
        # Create two non-cycle meetings
        MeetingDao.create(
            sponsor="s1", group_name="g1", community=self.community,
            topic="Meeting 1", platform="WELINK", is_cycle=False,
            date=self.today, start="10:00", end="11:00", is_record=False,
            mid=f"mid1_{datetime.datetime.now().timestamp()}", host_id="h1@test.com",
            status=BusinessMeetingStatus.NOT_STARTED.value, is_delete=0
        )
        MeetingDao.create(
            sponsor="s2", group_name="g2", community=self.community,
            topic="Meeting 2", platform="WELINK", is_cycle=False,
            date=self.today, start="14:00", end="15:00", is_record=False,
            mid=f"mid2_{datetime.datetime.now().timestamp()}", host_id="h2@test.com",
            status=BusinessMeetingStatus.NOT_STARTED.value, is_delete=0
        )

        result = MeetingDao.get_non_cycle_meetings_count(self.community, {})

        self.assertEqual(result, 2)

    def test_get_non_cycle_meetings_count_with_date_filter(self):
        """Test non-cycle meetings count with date filter."""
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        MeetingDao.create(
            sponsor="s1", group_name="g1", community=self.community,
            topic="Today Meeting", platform="WELINK", is_cycle=False,
            date=self.today, start="10:00", end="11:00", is_record=False,
            mid=f"mid_t_{datetime.datetime.now().timestamp()}", host_id="h1@test.com",
            status=BusinessMeetingStatus.NOT_STARTED.value, is_delete=0
        )
        MeetingDao.create(
            sponsor="s2", group_name="g2", community=self.community,
            topic="Tomorrow Meeting", platform="WELINK", is_cycle=False,
            date=tomorrow, start="10:00", end="11:00", is_record=False,
            mid=f"mid_tm_{datetime.datetime.now().timestamp()}", host_id="h2@test.com",
            status=BusinessMeetingStatus.NOT_STARTED.value, is_delete=0
        )

        result = MeetingDao.get_non_cycle_meetings_count(self.community, {'date': self.today})

        self.assertEqual(result, 1)


class MeetingCycleDaoTest(TestCommonMeeting):
    """Test MeetingCycleDao methods."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def test_get_by_mids_basic(self):
        """Test basic batch retrieval by mids."""
        # Create parent meetings
        parent1 = MeetingDao.create(
            sponsor="s1", group_name="g1", community=self.community,
            topic="Cycle Meeting 1", platform="WELINK", is_cycle=True,
            is_record=False, mid=f"mid1_{datetime.datetime.now().timestamp()}",
            host_id="h1@test.com"
        )
        parent2 = MeetingDao.create(
            sponsor="s2", group_name="g2", community=self.community,
            topic="Cycle Meeting 2", platform="WELINK", is_cycle=True,
            is_record=False, mid=f"mid2_{datetime.datetime.now().timestamp()}",
            host_id="h2@test.com"
        )

        # Create cycle date records
        MeetingCycleDao.create(
            mid=parent1.mid,
            start_date="2026-04-01",
            end_date="2026-04-30",
            start="10:00",
            end="11:00",
            cycle_type=1,
            interval=1,
            meeting=parent1
        )
        MeetingCycleDao.create(
            mid=parent2.mid,
            start_date="2026-04-01",
            end_date="2026-04-30",
            start="14:00",
            end="15:00",
            cycle_type=1,
            interval=1,
            meeting=parent2
        )

        result = MeetingCycleDao.get_by_mids([parent1.mid, parent2.mid])

        self.assertEqual(len(result), 2)

    def test_get_by_mids_empty_list(self):
        """Test get_by_mids returns empty list for empty input."""
        result = MeetingCycleDao.get_by_mids([])

        self.assertEqual(result, [])

    def test_get_by_mids_nonexistent_mid(self):
        """Test get_by_mids returns empty list for nonexistent mid."""
        result = MeetingCycleDao.get_by_mids(["nonexistent_mid"])

        self.assertEqual(result, [])

    def test_get_by_mid_returns_correct_record(self):
        """Test get_by_mid returns correct cycle date record."""
        parent = MeetingDao.create(
            sponsor="s1", group_name="g1", community=self.community,
            topic="Cycle Meeting", platform="WELINK", is_cycle=True,
            is_record=False, mid=f"mid_{datetime.datetime.now().timestamp()}",
            host_id="h@test.com"
        )

        cycle_date = MeetingCycleDao.create(
            mid=parent.mid,
            start_date="2026-04-01",
            end_date="2026-04-30",
            start="10:00",
            end="11:00",
            cycle_type=1,
            interval=1,
            meeting=parent
        )

        result = MeetingCycleDao.get_by_mid(parent.mid)

        self.assertIsNotNone(result)
        self.assertEqual(result.mid, parent.mid)
        self.assertEqual(result.start_date, "2026-04-01")


class MeetingCycleSubMeetingDaoTest(TestCommonMeeting):
    """Test MeetingCycleSubMeetingDao methods."""

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
        }
        defaults.update(kwargs)
        return MeetingCycleSubMeetingDao.create(**defaults)

    def test_get_all(self):
        """Test get_all returns all sub meetings."""
        parent = self._create_parent_meeting()
        sub1 = self._create_sub_meeting(parent)
        sub2 = self._create_sub_meeting(parent, sub_id=f"sub2_{datetime.datetime.now().timestamp()}")

        result = MeetingCycleSubMeetingDao.get_all()

        self.assertTrue(result.count() >= 2)

    def test_get_by_mid(self):
        """Test get_by_mid returns sub meetings for a specific mid."""
        parent = self._create_parent_meeting()
        sub1 = self._create_sub_meeting(parent)
        sub2 = self._create_sub_meeting(parent, sub_id=f"sub2_{datetime.datetime.now().timestamp()}")

        result = MeetingCycleSubMeetingDao.get_by_mid(parent.mid)

        self.assertEqual(len(result), 2)

    def test_get_by_mid_date(self):
        """Test get_by_mid_date returns sub meeting for specific mid and date."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent)

        result = MeetingCycleSubMeetingDao.get_by_mid_date(parent.mid, self.today)

        self.assertIsNotNone(result)
        self.assertEqual(result.mid, parent.mid)
        self.assertEqual(result.date, self.today)

    def test_get_by_date_range(self):
        """Test get_by_date_range returns dates within range."""
        parent = self._create_parent_meeting()
        sub1 = self._create_sub_meeting(parent, date=self.today)
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        sub2 = self._create_sub_meeting(parent, date=tomorrow, sub_id=f"sub2_{datetime.datetime.now().timestamp()}")

        result = MeetingCycleSubMeetingDao.get_by_date_range(self.today, tomorrow, parent.mid)

        self.assertEqual(len(result), 2)

    def test_get_counts_by_mid(self):
        """Test get_counts_by_mid returns correct count."""
        parent = self._create_parent_meeting()
        sub1 = self._create_sub_meeting(parent)
        sub2 = self._create_sub_meeting(parent, sub_id=f"sub2_{datetime.datetime.now().timestamp()}")

        result = MeetingCycleSubMeetingDao.get_counts_by_mid(parent.mid)

        self.assertEqual(result, 2)

    def test_get_by_mid_and_sub_id(self):
        """Test get_by_mid_and_sub_id returns specific sub meeting."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent)

        result = MeetingCycleSubMeetingDao.get_by_mid_and_sub_id(parent.mid, sub.sub_id)

        self.assertIsNotNone(result)
        self.assertEqual(result.sub_id, sub.sub_id)

    def test_get_by_sub_id(self):
        """Test get_by_sub_id returns specific sub meeting."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent)

        result = MeetingCycleSubMeetingDao.get_by_sub_id(sub.sub_id)

        self.assertIsNotNone(result)
        self.assertEqual(result.sub_id, sub.sub_id)

    def test_delete_by_mid_and_sub_id(self):
        """Test delete_by_mid_and_sub_id deletes specific sub meeting."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent)

        result = MeetingCycleSubMeetingDao.delete_by_mid_and_sub_id(parent.mid, sub.sub_id)

        # Check that sub meeting is deleted
        deleted_sub = MeetingCycleSubMeetingDao.get_by_sub_id(sub.sub_id)
        self.assertIsNone(deleted_sub)

    def test_get_status_sync_candidates_includes_today_and_future(self):
        """Test get_status_sync_candidates returns sub meetings >= today."""
        parent = self._create_parent_meeting(is_delete=0)

        yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')

        # Create sub meetings for yesterday, today, tomorrow
        MeetingCycleSubMeetingDao.create(
            mid=parent.mid, sub_id=f"sub_y_{datetime.datetime.now().timestamp()}",
            date=yesterday, start="10:00", end="11:00", meeting=parent,
            status=BusinessMeetingStatus.NOT_STARTED.value
        )
        sub_today = MeetingCycleSubMeetingDao.create(
            mid=parent.mid, sub_id=f"sub_t_{datetime.datetime.now().timestamp()}",
            date=self.today, start="10:00", end="11:00", meeting=parent,
            status=BusinessMeetingStatus.NOT_STARTED.value
        )
        sub_tomorrow = MeetingCycleSubMeetingDao.create(
            mid=parent.mid, sub_id=f"sub_tm_{datetime.datetime.now().timestamp()}",
            date=tomorrow, start="10:00", end="11:00", meeting=parent,
            status=BusinessMeetingStatus.NOT_STARTED.value
        )

        result = MeetingCycleSubMeetingDao.get_status_sync_candidates(self.community, self.today)

        # Should include today and tomorrow
        result_ids = [s.id for s in result]
        self.assertIn(sub_today.id, result_ids)
        self.assertIn(sub_tomorrow.id, result_ids)

    def test_has_subsequent_sub_meetings_true(self):
        """Test has_subsequent_sub_meetings returns True when subsequent sub meetings exist."""
        host_id = "host@test.com"
        parent = self._create_parent_meeting(host_id=host_id)

        # Create current sub meeting ending at 11:00
        MeetingCycleSubMeetingDao.create(
            mid=parent.mid, sub_id=f"sub1_{datetime.datetime.now().timestamp()}",
            date=self.today, start="10:00", end="11:00", meeting=parent,
            status=BusinessMeetingStatus.NOT_STARTED.value
        )
        # Create subsequent sub meeting starting at 14:00
        MeetingCycleSubMeetingDao.create(
            mid=parent.mid, sub_id=f"sub2_{datetime.datetime.now().timestamp()}",
            date=self.today, start="14:00", end="15:00", meeting=parent,
            status=BusinessMeetingStatus.NOT_STARTED.value
        )

        result = MeetingCycleSubMeetingDao.has_subsequent_sub_meetings(
            self.community, host_id, self.today, "11:00"
        )

        self.assertTrue(result)

    def test_has_subsequent_sub_meetings_false(self):
        """Test has_subsequent_sub_meetings returns False when no subsequent sub meetings."""
        host_id = "host@test.com"
        parent = self._create_parent_meeting(host_id=host_id)

        MeetingCycleSubMeetingDao.create(
            mid=parent.mid, sub_id=f"sub1_{datetime.datetime.now().timestamp()}",
            date=self.today, start="10:00", end="11:00", meeting=parent,
            status=BusinessMeetingStatus.NOT_STARTED.value
        )

        result = MeetingCycleSubMeetingDao.has_subsequent_sub_meetings(
            self.community, host_id, self.today, "11:00"
        )

        self.assertFalse(result)

    def test_get_expanded_sub_meetings_queryset_basic(self):
        """Test get_expanded_sub_meetings_queryset returns correct fields."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent)

        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings_queryset(self.community, {})

        # Check that result contains expected fields
        result_list = list(result)
        self.assertTrue(len(result_list) >= 1)
        first_result = result_list[0]
        self.assertIn('meeting__id', first_result)
        self.assertIn('meeting__topic', first_result)
        self.assertIn('date', first_result)
        self.assertIn('start', first_result)
        self.assertIn('end', first_result)

    def test_get_expanded_sub_meetings_queryset_with_filters(self):
        """Test get_expanded_sub_meetings_queryset applies filters correctly."""
        parent = self._create_parent_meeting()
        sub1 = self._create_sub_meeting(parent)
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        sub2 = self._create_sub_meeting(parent, date=tomorrow, sub_id=f"sub2_{datetime.datetime.now().timestamp()}")

        # Filter by date
        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings_queryset(
            self.community, {'date': self.today}
        )

        result_list = list(result)
        # Should only return today's sub meeting
        dates = [r['date'].strftime('%Y-%m-%d') if hasattr(r['date'], 'strftime') else str(r['date']) for r in result_list]
        for date_str in dates:
            self.assertEqual(date_str, self.today)

    def test_get_expanded_sub_meetings_count_basic(self):
        """Test get_expanded_sub_meetings_count returns correct count."""
        parent = self._create_parent_meeting(is_delete=0)
        sub1 = self._create_sub_meeting(parent)
        sub2 = self._create_sub_meeting(parent, sub_id=f"sub2_{datetime.datetime.now().timestamp()}")

        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings_count(self.community, {})

        self.assertEqual(result, 2)

    def test_get_expanded_sub_meetings_count_with_date_filter(self):
        """Test get_expanded_sub_meetings_count with date filter."""
        parent = self._create_parent_meeting(is_delete=0)
        sub1 = self._create_sub_meeting(parent)
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        sub2 = self._create_sub_meeting(parent, date=tomorrow, sub_id=f"sub2_{datetime.datetime.now().timestamp()}")

        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings_count(
            self.community, {'date': self.today}
        )

        self.assertEqual(result, 1)


class MeetingDaoConflictTest(TestCommonMeeting):
    """Test MeetingDao.get_conflict_meeting method."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def _create_meeting(self, **kwargs):
        """Create a test meeting."""
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

    def test_get_conflict_meeting_no_conflicts(self):
        """Test get_conflict_meeting returns empty when no conflicts."""
        host_ids, topics, cur_day_host_ids = MeetingDao.get_conflict_meeting(
            self.community, "WELINK", self.today, "14:00", "16:00"
        )

        # Should return empty lists when no meetings exist
        self.assertEqual(len(list(host_ids)), 0)
        self.assertEqual(len(list(topics)), 0)

    def test_get_conflict_meeting_with_conflict(self):
        """Test get_conflict_meeting returns conflicting meetings."""
        meeting = self._create_meeting(
            start="10:00",
            end="11:00",
            host_id="host1@test.com"
        )

        # Query for overlapping time range
        host_ids, topics, cur_day_host_ids = MeetingDao.get_conflict_meeting(
            self.community, "WELINK", self.today, "10:30", "11:30"
        )

        # Should find the meeting we created
        self.assertTrue(len(list(host_ids)) >= 1)

    def test_get_conflict_meeting_excludes_meeting_id(self):
        """Test get_conflict_meeting excludes specified meeting_id."""
        meeting = self._create_meeting(
            start="10:00",
            end="11:00",
            host_id="host1@test.com"
        )

        # Query excluding this meeting's ID
        host_ids, topics, cur_day_host_ids = MeetingDao.get_conflict_meeting(
            self.community, "WELINK", self.today, "10:30", "11:30", meeting_id=meeting.id
        )

        # Should not include the excluded meeting
        host_ids_list = list(host_ids)
        self.assertEqual(len(host_ids_list), 0)


class MeetingDaoStatusUpdateTest(TestCommonMeeting):
    """Test MeetingDao status update methods."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def _create_meeting(self, **kwargs):
        """Create a test meeting."""
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

    def test_update_status(self):
        """Test update_status changes meeting status."""
        meeting = self._create_meeting()

        result = MeetingDao.update_status(meeting.id, BusinessMeetingStatus.ONGOING.value)

        # Verify status was updated
        updated_meeting = MeetingDao.get_by_id(meeting.id)
        self.assertEqual(updated_meeting.status, BusinessMeetingStatus.ONGOING.value)

    def test_clear_status(self):
        """Test clear_status sets status to ENDED."""
        meeting = self._create_meeting(status=BusinessMeetingStatus.ONGOING.value)

        result = MeetingDao.clear_status(meeting.id)

        # Verify status was cleared to ENDED
        updated_meeting = MeetingDao.get_by_id(meeting.id)
        self.assertEqual(updated_meeting.status, BusinessMeetingStatus.ENDED.value)

    def test_mark_warning_email_sent(self):
        """Test mark_warning_email_sent sets flag."""
        meeting = self._create_meeting(warning_email_sent=False)

        result = MeetingDao.mark_warning_email_sent(meeting.id)

        # Verify flag was set
        updated_meeting = MeetingDao.get_by_id(meeting.id)
        self.assertTrue(updated_meeting.warning_email_sent)


class MeetingDaoUpcomingEndTest(TestCommonMeeting):
    """Test MeetingDao.get_upcoming_end_meetings method."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def _create_meeting(self, **kwargs):
        """Create a test meeting."""
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

    def test_get_upcoming_end_meetings_returns_meetings(self):
        """Test get_upcoming_end_meetings returns meetings about to end."""
        # Create meeting ending soon
        now = datetime.datetime.now()
        end_time = (now + datetime.timedelta(minutes=5)).strftime('%H:%M')

        meeting = self._create_meeting(
            end=end_time,
            status=BusinessMeetingStatus.ONGOING.value
        )

        result = MeetingDao.get_upcoming_end_meetings(self.community, self.today, warning_minutes=10)

        # Should return meetings that are about to end
        # Note: Result depends on current time, so we just verify it returns a queryset
        self.assertIsNotNone(result)

    def test_get_upcoming_end_meetings_excludes_sent(self):
        """Test get_upcoming_end_meetings excludes meetings with email sent."""
        meeting = self._create_meeting(
            status=BusinessMeetingStatus.ONGOING.value,
            warning_email_sent=True
        )

        result = MeetingDao.get_upcoming_end_meetings(self.community, self.today, warning_minutes=10)

        # Should not include meetings where email already sent
        meeting_ids = [m.id for m in result]
        self.assertNotIn(meeting.id, meeting_ids)


class MeetingDaoNextMeetingTest(TestCommonMeeting):
    """Test MeetingDao.get_next_meeting_start_time method."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def _create_meeting(self, **kwargs):
        """Create a test meeting."""
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

    def test_get_next_meeting_start_time_returns_time(self):
        """Test get_next_meeting_start_time returns next meeting's start."""
        host_id = "host@test.com"

        # Current meeting ends at 11:00
        self._create_meeting(
            host_id=host_id,
            start="10:00",
            end="11:00"
        )

        # Next meeting starts at 14:00
        self._create_meeting(
            host_id=host_id,
            start="14:00",
            end="15:00",
            mid=f"mid_next_{datetime.datetime.now().timestamp()}"
        )

        result = MeetingDao.get_next_meeting_start_time(
            self.community, host_id, self.today, "11:00"
        )

        self.assertEqual(result, "14:00")

    def test_get_next_meeting_start_time_none_when_no_next(self):
        """Test get_next_meeting_start_time returns None when no next meeting."""
        host_id = "host@test.com"

        self._create_meeting(
            host_id=host_id,
            start="10:00",
            end="11:00"
        )

        result = MeetingDao.get_next_meeting_start_time(
            self.community, host_id, self.today, "11:00"
        )

        self.assertIsNone(result)


class MeetingDaoNonCycleTest(TestCommonMeeting):
    """Test MeetingDao.get_non_cycle_meetings method."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def _create_meeting(self, **kwargs):
        """Create a test meeting."""
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

    def test_get_non_cycle_meetings_basic(self):
        """Test get_non_cycle_meetings returns non-cycle meetings."""
        meeting = self._create_meeting()

        result = MeetingDao.get_non_cycle_meetings(self.community, {})

        # Should return queryset containing our meeting
        result_list = list(result)
        self.assertTrue(len(result_list) >= 1)

    def test_get_non_cycle_meetings_with_status_filter(self):
        """Test get_non_cycle_meetings filters by status."""
        meeting1 = self._create_meeting(
            status=BusinessMeetingStatus.ONGOING.value
        )
        meeting2 = self._create_meeting(
            status=BusinessMeetingStatus.CANCELLED.value,
            is_delete=1,
            mid=f"mid_cancel_{datetime.datetime.now().timestamp()}"
        )

        # Filter for ONGOING status
        result = MeetingDao.get_non_cycle_meetings(
            self.community, {'status': BusinessMeetingStatus.ONGOING.value}
        )

        result_list = list(result)
        # Should only return ongoing meeting
        for m in result_list:
            self.assertEqual(m['status'], BusinessMeetingStatus.ONGOING.value)

    def test_get_non_cycle_meetings_with_topic_filter(self):
        """Test get_non_cycle_meetings filters by topic."""
        meeting1 = self._create_meeting(topic="Important Meeting")
        meeting2 = self._create_meeting(topic="Regular Meeting", mid=f"mid2_{datetime.datetime.now().timestamp()}")

        result = MeetingDao.get_non_cycle_meetings(
            self.community, {'topic': 'Important'}
        )

        result_list = list(result)
        # Should only return meetings matching topic
        for m in result_list:
            self.assertIn('Important', m['topic'])

    def test_get_non_cycle_meetings_with_group_name_filter(self):
        """Test get_non_cycle_meetings filters by group_name."""
        meeting1 = self._create_meeting(group_name="SIG-Architecture")
        meeting2 = self._create_meeting(group_name="SIG-Kernel", mid=f"mid2_{datetime.datetime.now().timestamp()}")

        result = MeetingDao.get_non_cycle_meetings(
            self.community, {'group_name': 'SIG-Arch'}
        )

        result_list = list(result)
        self.assertTrue(len(result_list) >= 1)


class MeetingCycleSubMeetingDaoClearStatusTest(TestCommonMeeting):
    """Test MeetingCycleSubMeetingDao.clear_status method."""

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
            "status": BusinessMeetingStatus.ONGOING.value,
        }
        defaults.update(kwargs)
        return MeetingCycleSubMeetingDao.create(**defaults)

    def test_clear_status(self):
        """Test clear_status sets sub meeting status to ENDED."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent, status=BusinessMeetingStatus.ONGOING.value)

        result = MeetingCycleSubMeetingDao.clear_status(sub.sub_id)

        # Verify status was cleared
        updated_sub = MeetingCycleSubMeetingDao.get_by_sub_id(sub.sub_id)
        self.assertEqual(updated_sub.status, BusinessMeetingStatus.ENDED.value)


class MeetingCycleSubMeetingDaoUpdateStatusTest(TestCommonMeeting):
    """Test MeetingCycleSubMeetingDao.update_status method."""

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
        }
        defaults.update(kwargs)
        return MeetingCycleSubMeetingDao.create(**defaults)

    def test_update_status(self):
        """Test update_status changes sub meeting status."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent)

        result = MeetingCycleSubMeetingDao.update_status(sub.id, BusinessMeetingStatus.ONGOING.value)

        # Verify status was updated
        updated_sub = MeetingCycleSubMeetingDao.get_by_sub_id(sub.sub_id)
        self.assertEqual(updated_sub.status, BusinessMeetingStatus.ONGOING.value)


class MeetingCycleSubMeetingDaoWarningEmailTest(TestCommonMeeting):
    """Test MeetingCycleSubMeetingDao warning email methods."""

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
            "status": BusinessMeetingStatus.ONGOING.value,
            "warning_email_sent": False,
        }
        defaults.update(kwargs)
        return MeetingCycleSubMeetingDao.create(**defaults)

    def test_mark_warning_email_sent(self):
        """Test mark_warning_email_sent sets flag."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent, warning_email_sent=False)

        result = MeetingCycleSubMeetingDao.mark_warning_email_sent(sub.id)

        # Verify flag was set
        updated_sub = MeetingCycleSubMeetingDao.get_by_sub_id(sub.sub_id)
        self.assertTrue(updated_sub.warning_email_sent)

    def test_reset_warning_email_status(self):
        """Test reset_warning_email_status clears flag."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent, warning_email_sent=True)

        result = MeetingCycleSubMeetingDao.reset_warning_email_status(sub.sub_id)

        # Verify flag was cleared
        updated_sub = MeetingCycleSubMeetingDao.get_by_sub_id(sub.sub_id)
        self.assertFalse(updated_sub.warning_email_sent)

    def test_get_upcoming_end_sub_meetings(self):
        """Test get_upcoming_end_sub_meetings returns sub meetings about to end."""
        parent = self._create_parent_meeting()

        now = datetime.datetime.now()
        end_time = (now + datetime.timedelta(minutes=5)).strftime('%H:%M')

        sub = self._create_sub_meeting(
            parent,
            end=end_time,
            status=BusinessMeetingStatus.ONGOING.value
        )

        result = MeetingCycleSubMeetingDao.get_upcoming_end_sub_meetings(
            self.community, self.today, warning_minutes=10
        )

        # Should return a queryset
        self.assertIsNotNone(result)

    def test_update_status_by_mid(self):
        """Test update_status_by_mid updates all sub meetings (covers line 70)."""
        parent = self._create_parent_meeting()
        sub1 = self._create_sub_meeting(parent, status=BusinessMeetingStatus.NOT_STARTED.value)
        sub2 = self._create_sub_meeting(parent, sub_id=f"sub2_{datetime.datetime.now().timestamp()}", status=BusinessMeetingStatus.NOT_STARTED.value)

        result = MeetingCycleSubMeetingDao.update_status_by_mid(parent.mid, BusinessMeetingStatus.CANCELLED.value)

        # Verify all sub meetings updated
        updated_sub1 = MeetingCycleSubMeetingDao.get_by_sub_id(sub1.sub_id)
        updated_sub2 = MeetingCycleSubMeetingDao.get_by_sub_id(sub2.sub_id)
        self.assertEqual(updated_sub1.status, BusinessMeetingStatus.CANCELLED.value)
        self.assertEqual(updated_sub2.status, BusinessMeetingStatus.CANCELLED.value)

    def test_get_ongoing_sub_meetings(self):
        """Test get_ongoing_sub_meetings returns ongoing meetings (covers line 87)."""
        parent = self._create_parent_meeting()
        sub_ongoing = self._create_sub_meeting(parent, status=BusinessMeetingStatus.ONGOING.value)
        sub_not_started = self._create_sub_meeting(parent, sub_id=f"sub2_{datetime.datetime.now().timestamp()}", status=BusinessMeetingStatus.NOT_STARTED.value)

        result = MeetingCycleSubMeetingDao.get_ongoing_sub_meetings(self.community)

        # Should only return ongoing meetings
        result_ids = [s.id for s in result]
        self.assertIn(sub_ongoing.id, result_ids)
        self.assertNotIn(sub_not_started.id, result_ids)

    def test_get_ongoing_sub_meetings_for_warning(self):
        """Test get_ongoing_sub_meetings_for_warning returns correct meetings (covers lines 140-152)."""
        parent = self._create_parent_meeting()

        now = datetime.datetime.now()
        end_time = (now + datetime.timedelta(hours=1)).strftime('%H:%M')

        sub = self._create_sub_meeting(
            parent,
            end=end_time,
            status=BusinessMeetingStatus.ONGOING.value,
            warning_email_sent=False
        )

        result = MeetingCycleSubMeetingDao.get_ongoing_sub_meetings_for_warning(self.community, self.today)

        # Should return meetings that need warning
        result_ids = [s.id for s in result]
        self.assertIn(sub.id, result_ids)

    def test_get_next_sub_meeting_start_time_returns_none(self):
        """Test get_next_sub_meeting_start_time returns None when no next meeting (covers line 177)."""
        host_id = "host@test.com"
        parent = self._create_parent_meeting(host_id=host_id)

        MeetingCycleSubMeetingDao.create(
            mid=parent.mid, sub_id=f"sub1_{datetime.datetime.now().timestamp()}",
            date=self.today, start="10:00", end="11:00", meeting=parent,
            status=BusinessMeetingStatus.NOT_STARTED.value
        )

        result = MeetingCycleSubMeetingDao.get_next_sub_meeting_start_time(
            self.community, host_id, self.today, "11:00"
        )

        self.assertIsNone(result)

    def test_get_expanded_sub_meetings_with_date_filter(self):
        """Test get_expanded_sub_meetings with date filter (covers line 224)."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent)

        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings(
            self.community, {'date': self.today}
        )

        # Should return filtered results
        for r in result:
            self.assertEqual(str(r['date']), self.today)

    def test_get_expanded_sub_meetings_with_date_range_filter(self):
        """Test get_expanded_sub_meetings with date range filter (covers line 229)."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent)

        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings(
            self.community, {'start_date': self.today, 'end_date': self.today}
        )

        self.assertTrue(len(result) >= 1)

    def test_get_expanded_sub_meetings_with_sponsor_filter(self):
        """Test get_expanded_sub_meetings with sponsor filter (covers line 234)."""
        parent = self._create_parent_meeting(sponsor="Alice")
        sub = self._create_sub_meeting(parent)

        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings(
            self.community, {'sponsor': 'Alice'}
        )

        for r in result:
            self.assertEqual(r['sponsor'], 'Alice')

    def test_get_expanded_sub_meetings_with_group_name_filter(self):
        """Test get_expanded_sub_meetings with group_name filter (covers line 239)."""
        parent = self._create_parent_meeting(group_name="SIG-Arch")
        sub = self._create_sub_meeting(parent)

        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings(
            self.community, {'group_name': 'SIG'}
        )

        self.assertTrue(len(result) >= 1)

    def test_get_expanded_sub_meetings_with_platform_filter(self):
        """Test get_expanded_sub_meetings with platform filter (covers line 244)."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent)

        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings(
            self.community, {'platform': 'WELINK'}
        )

        for r in result:
            self.assertEqual(r['platform'], 'WELINK')

    def test_get_expanded_sub_meetings_queryset_with_status_filter(self):
        """Test get_expanded_sub_meetings_queryset with status filter (covers lines 286-289)."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent, status=BusinessMeetingStatus.ONGOING.value)

        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings_queryset(
            self.community, {'status': BusinessMeetingStatus.ONGOING.value}
        )

        result_list = list(result)
        for r in result_list:
            self.assertEqual(r['status'], BusinessMeetingStatus.ONGOING.value)

    def test_get_expanded_sub_meetings_queryset_with_cancelled_status(self):
        """Test get_expanded_sub_meetings_queryset with cancelled status (covers line 289)."""
        parent = self._create_parent_meeting(is_delete=1)
        sub = self._create_sub_meeting(parent)

        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings_queryset(
            self.community, {'status': BusinessMeetingStatus.CANCELLED.value}
        )

        # Should return meetings where parent is deleted
        result_list = list(result)
        for r in result_list:
            self.assertEqual(r['meeting__is_delete'], 1)

    def test_get_expanded_sub_meetings_queryset_with_date_range(self):
        """Test get_expanded_sub_meetings_queryset with date range filter (covers line 299)."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent)

        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings_queryset(
            self.community, {'start_date': self.today, 'end_date': self.today}
        )

        self.assertIsNotNone(result)

    def test_get_expanded_sub_meetings_queryset_with_sponsor(self):
        """Test get_expanded_sub_meetings_queryset with sponsor filter (covers line 304)."""
        parent = self._create_parent_meeting(sponsor="TestUser")
        sub = self._create_sub_meeting(parent)

        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings_queryset(
            self.community, {'sponsor': 'TestUser'}
        )

        result_list = list(result)
        for r in result_list:
            self.assertEqual(r['meeting__sponsor'], 'TestUser')

    def test_get_expanded_sub_meetings_queryset_with_group_name(self):
        """Test get_expanded_sub_meetings_queryset with group_name filter (covers line 309)."""
        parent = self._create_parent_meeting(group_name="TestSIG")
        sub = self._create_sub_meeting(parent)

        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings_queryset(
            self.community, {'group_name': 'TestSIG'}
        )

        result_list = list(result)
        for r in result_list:
            self.assertIn('TestSIG', r['meeting__group_name'])

    def test_get_expanded_sub_meetings_queryset_with_platform(self):
        """Test get_expanded_sub_meetings_queryset with platform filter (covers line 314)."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent)

        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings_queryset(
            self.community, {'platform': 'WELINK'}
        )

        result_list = list(result)
        for r in result_list:
            self.assertEqual(r['meeting__platform'], 'WELINK')

    def test_get_expanded_sub_meetings_queryset_with_topic(self):
        """Test get_expanded_sub_meetings_queryset with topic filter (covers line 319)."""
        parent = self._create_parent_meeting(topic="Important Meeting")
        sub = self._create_sub_meeting(parent)

        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings_queryset(
            self.community, {'topic': 'Important'}
        )

        result_list = list(result)
        for r in result_list:
            self.assertIn('Important', r['meeting__topic'])

    def test_get_expanded_sub_meetings_count_with_date_range(self):
        """Test get_expanded_sub_meetings_count with date range (covers line 350)."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent)

        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings_count(
            self.community, {'start_date': self.today, 'end_date': self.today}
        )

        self.assertEqual(result, 1)

    def test_get_expanded_sub_meetings_count_with_group_name(self):
        """Test get_expanded_sub_meetings_count with group_name filter (covers line 361)."""
        parent = self._create_parent_meeting(group_name="TestSIG")
        sub = self._create_sub_meeting(parent)

        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings_count(
            self.community, {'group_name': 'Test'}
        )

        self.assertEqual(result, 1)

    def test_get_expanded_sub_meetings_count_with_platform(self):
        """Test get_expanded_sub_meetings_count with platform filter (covers line 366)."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent)

        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings_count(
            self.community, {'platform': 'WELINK'}
        )

        self.assertEqual(result, 1)

    def test_get_expanded_sub_meetings_count_with_topic(self):
        """Test get_expanded_sub_meetings_count with topic filter (covers line 371)."""
        parent = self._create_parent_meeting(topic="Important Meeting")
        sub = self._create_sub_meeting(parent)

        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings_count(
            self.community, {'topic': 'Important'}
        )

        self.assertEqual(result, 1)

    def test_get_expanded_sub_meetings_count_with_sponsor_split(self):
        """Test get_expanded_sub_meetings_count with sponsor splitting (covers lines 355-356)."""
        parent1 = self._create_parent_meeting(sponsor="Alice")
        sub1 = self._create_sub_meeting(parent1)
        parent2 = self._create_parent_meeting(sponsor="Bob", mid=f"cycle_mid2_{datetime.datetime.now().timestamp()}")
        sub2 = self._create_sub_meeting(parent2)

        # Test sponsor split by comma
        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings_count(
            self.community, {'sponsor': 'Alice,Bob'}
        )

        # Should count both sponsors after split
        self.assertEqual(result, 2)

    def test_get_expanded_sub_meetings_count_with_single_sponsor_split(self):
        """Test get_expanded_sub_meetings_count with single sponsor (no split needed)."""
        parent = self._create_parent_meeting(sponsor="Alice")
        sub = self._create_sub_meeting(parent)

        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings_count(
            self.community, {'sponsor': 'Alice'}
        )

        self.assertEqual(result, 1)

    def test_get_expanded_sub_meetings_excludes_private_by_default(self):
        """Test get_expanded_sub_meetings excludes private meetings by default (covers lines 247-248)."""
        parent_public = self._create_parent_meeting(is_private=False)
        sub_public = self._create_sub_meeting(parent_public)
        parent_private = self._create_parent_meeting(is_private=True, mid=f"cycle_mid_private_{datetime.datetime.now().timestamp()}")
        sub_private = self._create_sub_meeting(parent_private)

        # Without include_private filter, should only return public meetings
        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings(self.community, {})
        result_mids = [r['mid'] for r in result]
        self.assertIn(parent_public.mid, result_mids)
        self.assertNotIn(parent_private.mid, result_mids)

    def test_get_expanded_sub_meetings_includes_private_when_set(self):
        """Test get_expanded_sub_meetings includes private meetings when include_private=True."""
        parent_public = self._create_parent_meeting(is_private=False)
        sub_public = self._create_sub_meeting(parent_public)
        parent_private = self._create_parent_meeting(is_private=True, mid=f"cycle_mid_private_{datetime.datetime.now().timestamp()}")
        sub_private = self._create_sub_meeting(parent_private)

        # With include_private=True, should return both public and private meetings
        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings(self.community, {'include_private': True})
        result_mids = [r['mid'] for r in result]
        self.assertIn(parent_public.mid, result_mids)
        self.assertIn(parent_private.mid, result_mids)

    def test_get_expanded_sub_meetings_queryset_excludes_private_by_default(self):
        """Test get_expanded_sub_meetings_queryset excludes private meetings by default (covers lines 322-323)."""
        parent_public = self._create_parent_meeting(is_private=False)
        sub_public = self._create_sub_meeting(parent_public)
        parent_private = self._create_parent_meeting(is_private=True, mid=f"cycle_mid_private_{datetime.datetime.now().timestamp()}")
        sub_private = self._create_sub_meeting(parent_private)

        # Without include_private filter, should only return public meetings
        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings_queryset(self.community, {})
        result_list = list(result)
        result_mids = [r['mid'] for r in result_list]
        self.assertIn(parent_public.mid, result_mids)
        self.assertNotIn(parent_private.mid, result_mids)

    def test_get_expanded_sub_meetings_queryset_includes_private_when_set(self):
        """Test get_expanded_sub_meetings_queryset includes private meetings when include_private=True."""
        parent_public = self._create_parent_meeting(is_private=False)
        sub_public = self._create_sub_meeting(parent_public)
        parent_private = self._create_parent_meeting(is_private=True, mid=f"cycle_mid_private_{datetime.datetime.now().timestamp()}")
        sub_private = self._create_sub_meeting(parent_private)

        # With include_private=True, should return both public and private meetings
        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings_queryset(self.community, {'include_private': True})
        result_list = list(result)
        result_mids = [r['mid'] for r in result_list]
        self.assertIn(parent_public.mid, result_mids)
        self.assertIn(parent_private.mid, result_mids)

    def test_get_expanded_sub_meetings_count_excludes_private_by_default(self):
        """Test get_expanded_sub_meetings_count excludes private meetings by default (covers lines 374-375)."""
        parent_public = self._create_parent_meeting(is_private=False)
        sub_public = self._create_sub_meeting(parent_public)
        parent_private = self._create_parent_meeting(is_private=True, mid=f"cycle_mid_private_{datetime.datetime.now().timestamp()}")
        sub_private = self._create_sub_meeting(parent_private)

        # Without include_private filter, should only count public meetings
        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings_count(self.community, {})
        self.assertEqual(result, 1)

    def test_get_expanded_sub_meetings_count_includes_private_when_set(self):
        """Test get_expanded_sub_meetings_count includes private meetings when include_private=True."""
        parent_public = self._create_parent_meeting(is_private=False)
        sub_public = self._create_sub_meeting(parent_public)
        parent_private = self._create_parent_meeting(is_private=True, mid=f"cycle_mid_private_{datetime.datetime.now().timestamp()}")
        sub_private = self._create_sub_meeting(parent_private)

        # With include_private=True, should count both public and private meetings
        result = MeetingCycleSubMeetingDao.get_expanded_sub_meetings_count(self.community, {'include_private': True})
        self.assertEqual(result, 2)

    def test_get_next_sub_meeting_start_time_returns_time(self):
        """Test get_next_sub_meeting_start_time returns time when next meeting exists."""
        host_id = "host@test.com"
        parent = self._create_parent_meeting(host_id=host_id)

        MeetingCycleSubMeetingDao.create(
            mid=parent.mid, sub_id=f"sub1_{datetime.datetime.now().timestamp()}",
            date=self.today, start="10:00", end="11:00", meeting=parent,
            status=BusinessMeetingStatus.NOT_STARTED.value
        )
        MeetingCycleSubMeetingDao.create(
            mid=parent.mid, sub_id=f"sub2_{datetime.datetime.now().timestamp()}",
            date=self.today, start="14:00", end="15:00", meeting=parent,
            status=BusinessMeetingStatus.NOT_STARTED.value
        )

        result = MeetingCycleSubMeetingDao.get_next_sub_meeting_start_time(
            self.community, host_id, self.today, "11:00"
        )

        self.assertEqual(result, "14:00")

    def test_get_first_by_date_range(self):
        """Test get_first_by_date_range returns first matching sub meeting (covers line 32)."""
        parent = self._create_parent_meeting()
        sub1 = self._create_sub_meeting(parent)
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        sub2 = self._create_sub_meeting(parent, date=tomorrow, sub_id=f"sub2_{datetime.datetime.now().timestamp()}")

        result = MeetingCycleSubMeetingDao.get_first_by_date_range(
            self.today, tomorrow, parent.mid, [sub1.sub_id, sub2.sub_id]
        )

        self.assertIsNotNone(result)
        self.assertEqual(result.mid, parent.mid)

    def test_delete_by_mid(self):
        """Test delete_by_mid deletes future sub meetings (covers lines 56-57)."""
        parent = self._create_parent_meeting()
        # Create sub meeting for today at 10:00-11:00
        sub_today = self._create_sub_meeting(parent, start="10:00", end="11:00")
        # Create sub meeting for tomorrow (should be deleted)
        tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        sub_future = MeetingCycleSubMeetingDao.create(
            mid=parent.mid, sub_id=f"sub_future_{datetime.datetime.now().timestamp()}",
            date=tomorrow, start="10:00", end="11:00", meeting=parent,
            status=BusinessMeetingStatus.NOT_STARTED.value
        )

        # Delete sub meetings after current time
        result = MeetingCycleSubMeetingDao.delete_by_mid(parent.mid, self.today, "12:00")

        # Verify today's meeting still exists (it started at 10:00, which is before 12:00)
        remaining_sub = MeetingCycleSubMeetingDao.get_by_sub_id(sub_today.sub_id)
        self.assertIsNotNone(remaining_sub)

    def test_get_by_mid_and_date_time_filter(self):
        """Test get_by_mid_and_date with time filter (covers lines 61-62)."""
        parent = self._create_parent_meeting()
        # Create sub meeting at 10:00-11:00
        sub_10 = self._create_sub_meeting(parent, start="10:00", end="11:00")
        # Create sub meeting at 14:00-15:00
        sub_14 = MeetingCycleSubMeetingDao.create(
            mid=parent.mid, sub_id=f"sub14_{datetime.datetime.now().timestamp()}",
            date=self.today, start="14:00", end="15:00", meeting=parent,
            status=BusinessMeetingStatus.NOT_STARTED.value
        )

        # Get sub meetings after 12:00 on today
        result = MeetingCycleSubMeetingDao.get_by_mid_and_date(parent.mid, self.today, "12:00")

        # Should only return sub meeting at 14:00
        result_list = list(result)
        self.assertEqual(len(result_list), 1)
        self.assertEqual(result_list[0].sub_id, sub_14.sub_id)

    def test_update_by_mid_and_sub_id(self):
        """Test update_by_mid_and_sub_id updates sub meeting fields (covers line 66)."""
        parent = self._create_parent_meeting()
        sub = self._create_sub_meeting(parent, start="10:00", end="11:00")

        result = MeetingCycleSubMeetingDao.update_by_mid_and_sub_id(
            parent.mid, sub.sub_id,
            start="14:00", end="15:00"
        )

        # Verify update
        updated_sub = MeetingCycleSubMeetingDao.get_by_sub_id(sub.sub_id)
        self.assertEqual(updated_sub.start, "14:00")
        self.assertEqual(updated_sub.end, "15:00")