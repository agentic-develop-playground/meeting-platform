#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
"""
Unit tests for inner.py controller views.

Tests include:
- ForceEndMeetingView: POST method tests
- MeetingListView: GET method tests with filters, pagination, ordering
- MeetingSponsorView: GET method tests
"""
import datetime
import json
from unittest import mock

from django.test import RequestFactory
from rest_framework.test import APITestCase, APIClient
from rest_framework.request import Request

from meeting.infrastructure.dao.meeting_dao import MeetingDao
from meeting.infrastructure.dao.meeting_cycle_dao import MeetingCycleDao
from meeting.infrastructure.dao.meeting_cycle_sub_dao import MeetingCycleSubMeetingDao
from meeting.domain.primitive.meeting_status import BusinessMeetingStatus
from meeting.domain.primitive.cycle_type import CycleType
from meeting.controller.inner import ForceEndMeetingView, MeetingListView, MeetingSponsorView
from meeting_platform.test.meeting.test_base import TestCommonMeeting
from meeting_platform.utils.ret_code import RetCode


class ForceEndMeetingViewTest(TestCommonMeeting):
    """Test ForceEndMeetingView POST method."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')
        self.user = self.create_user()
        self.enable_client_auth(self.user.username)

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
        }
        defaults.update(kwargs)
        return MeetingDao.create(**defaults)

    def _create_cycle_meeting(self, **kwargs):
        """Create a cycle test meeting."""
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

    def _create_sub_meeting(self, parent, **kwargs):
        """Create a sub meeting."""
        defaults = {
            "mid": parent.mid,
            "sub_id": f"sub_{datetime.datetime.now().timestamp()}",
            "date": self.today,
            "start": "10:00",
            "end": "11:00",
            "meeting": parent,
            "status": BusinessMeetingStatus.ONGOING.value,
        }
        defaults.update(kwargs)
        return MeetingCycleSubMeetingDao.create(**defaults)

    @mock.patch('meeting.application.meeting.MeetingApp.force_stop_meeting')
    def test_post_non_cycle_success(self, mock_force_stop):
        """Test POST for non-cycle meeting force end."""
        meeting = self._create_meeting()

        view = ForceEndMeetingView()
        request = mock.MagicMock()
        request.data = {'meeting_id': meeting.id}

        response = view.post(request)

        mock_force_stop.assert_called_once_with(meeting.id, None)
        self.assertEqual(response.status_code, 200)

    @mock.patch('meeting.application.meeting.MeetingApp.force_stop_meeting')
    def test_post_cycle_sub_meeting_success(self, mock_force_stop):
        """Test POST for cycle sub meeting force end."""
        parent = self._create_cycle_meeting()
        sub = self._create_sub_meeting(parent)

        view = ForceEndMeetingView()
        request = mock.MagicMock()
        request.data = {'meeting_id': parent.id, 'sub_id': sub.sub_id}

        response = view.post(request)

        mock_force_stop.assert_called_once_with(parent.id, sub.sub_id)
        self.assertEqual(response.status_code, 200)

    def test_post_missing_meeting_id(self):
        """Test POST raises error when meeting_id is missing."""
        view = ForceEndMeetingView()
        request = mock.MagicMock()
        request.data = {'sub_id': 'some_sub_id'}

        # Should raise MyValidationError
        from meeting_platform.utils.ret_api import MyValidationError
        with self.assertRaises(MyValidationError):
            view.post(request)

    @mock.patch('meeting.application.meeting.MeetingApp.force_stop_meeting')
    def test_post_meeting_not_found(self, mock_force_stop):
        """Test POST raises error when meeting is not found."""
        from meeting_platform.utils.ret_api import MyValidationError
        mock_force_stop.side_effect = MyValidationError(RetCode.STATUS_PARAMETER_ERROR)

        view = ForceEndMeetingView()
        request = mock.MagicMock()
        request.data = {'meeting_id': 99999}

        # Should raise MyValidationError
        with self.assertRaises(MyValidationError):
            view.post(request)


class MeetingListViewTest(TestCommonMeeting):
    """Test MeetingListView GET method."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')
        self.user = self.create_user()
        self.enable_client_auth(self.user.username)

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

    @mock.patch('meeting.application.meeting.MeetingApp.get_merged_meeting_list')
    def test_get_basic_list(self, mock_get_merged):
        """Test GET returns merged meeting list."""
        mock_get_merged.return_value = {
            'total': 2,
            'list': [
                {'id': 1, 'mid': 'mid_1', 'topic': 'Meeting 1', 'sponsor': 'Alice', 'date': self.today, 'group_name': 'SIG1', 'community': self.community, 'platform': 'WELINK', 'start': '10:00', 'end': '11:00', 'is_cycle': False, 'status': 0},
                {'id': 2, 'mid': 'mid_2', 'topic': 'Meeting 2', 'sponsor': 'Bob', 'date': self.today, 'group_name': 'SIG2', 'community': self.community, 'platform': 'WELINK', 'start': '14:00', 'end': '15:00', 'is_cycle': False, 'status': 0},
            ],
            'page': 1,
            'size': 10
        }

        view = MeetingListView()
        django_request = self.factory.get(
            '/inner/meeting/list/',
            {'community': self.community}
        )
        request = Request(django_request)

        response = view.get(request)

        mock_get_merged.assert_called_once()
        self.assertEqual(response.status_code, 200)

    @mock.patch('meeting.application.meeting.MeetingApp.get_merged_meeting_list')
    def test_get_with_filters(self, mock_get_merged):
        """Test GET with filters."""
        mock_get_merged.return_value = {
            'total': 1,
            'list': [{'id': 1, 'mid': 'mid_1', 'topic': 'Filtered Meeting', 'group_name': 'SIG1', 'community': self.community, 'platform': 'WELINK', 'sponsor': 'Alice', 'date': self.today, 'start': '10:00', 'end': '11:00', 'is_cycle': False, 'status': 0}],
            'page': 1,
            'size': 10
        }

        view = MeetingListView()
        django_request = self.factory.get(
            '/inner/meeting/list/',
            {
                'community': self.community,
                'sponsor': 'Alice',
                'date': self.today,
                'platform': 'WELINK'
            }
        )
        request = Request(django_request)

        response = view.get(request)

        mock_get_merged.assert_called_once()
        # Verify filters are passed correctly
        call_args = mock_get_merged.call_args
        filters = call_args[1]['filters']
        self.assertEqual(filters['sponsor'], 'Alice')
        self.assertEqual(filters['date'], self.today)

    @mock.patch('meeting.application.meeting.MeetingApp.get_merged_meeting_list')
    def test_get_pagination(self, mock_get_merged):
        """Test GET with pagination parameters."""
        mock_get_merged.return_value = {
            'total': 50,
            'list': [],
            'page': 2,
            'size': 20
        }

        view = MeetingListView()
        django_request = self.factory.get(
            '/inner/meeting/list/',
            {
                'community': self.community,
                'page': 2,
                'size': 20
            }
        )
        request = Request(django_request)

        response = view.get(request)

        mock_get_merged.assert_called_once()
        call_args = mock_get_merged.call_args
        self.assertEqual(call_args[1]['page'], 2)
        self.assertEqual(call_args[1]['page_size'], 20)

    @mock.patch('meeting.application.meeting.MeetingApp.get_merged_meeting_list')
    def test_get_ordering(self, mock_get_merged):
        """Test GET with ordering parameters."""
        mock_get_merged.return_value = {
            'total': 10,
            'list': [],
            'page': 1,
            'size': 10
        }

        view = MeetingListView()
        django_request = self.factory.get(
            '/inner/meeting/list/',
            {
                'community': self.community,
                'order_by': 'start',
                'order_type': 'desc'
            }
        )
        request = Request(django_request)

        response = view.get(request)

        mock_get_merged.assert_called_once()
        call_args = mock_get_merged.call_args
        self.assertEqual(call_args[1]['order_by'], 'start')
        self.assertEqual(call_args[1]['order_type'], 'desc')

    @mock.patch('meeting.application.meeting.MeetingApp.get_merged_meeting_list')
    def test_get_merged_results(self, mock_get_merged):
        """Test GET returns merged results."""
        mock_get_merged.return_value = {
            'total': 5,
            'list': [
                {'id': 1, 'mid': 'mid_1', 'is_cycle': False, 'sub_id': None, 'group_name': 'SIG1', 'community': self.community, 'platform': 'WELINK', 'topic': 'Meeting 1', 'sponsor': 'Alice', 'date': self.today, 'start': '10:00', 'end': '11:00', 'status': 0},
                {'id': 2, 'mid': 'mid_2', 'is_cycle': True, 'sub_id': 'sub_1', 'group_name': 'SIG2', 'community': self.community, 'platform': 'WELINK', 'topic': 'Cycle Meeting', 'sponsor': 'Bob', 'date': self.today, 'start': '14:00', 'end': '15:00', 'status': 0},
            ],
            'page': 1,
            'size': 10
        }

        view = MeetingListView()
        django_request = self.factory.get(
            '/inner/meeting/list/',
            {'community': self.community}
        )
        request = Request(django_request)

        response = view.get(request)

        # Verify response structure
        self.assertEqual(response.status_code, 200)


class MeetingSponsorViewTest(TestCommonMeeting):
    """Test MeetingSponsorView GET method."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')
        self.user = self.create_user()
        self.enable_client_auth(self.user.username)

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
        }
        defaults.update(kwargs)
        return MeetingDao.create(**defaults)

    @mock.patch('meeting.application.meeting.MeetingApp.get_meeting_sponsors')
    def test_get_sponsors_success(self, mock_get_sponsors):
        """Test GET returns sponsors list."""
        mock_get_sponsors.return_value = ['Alice', 'Bob', 'Charlie']

        view = MeetingSponsorView()
        django_request = self.factory.get(
            '/inner/sponsors/',
            {'community': self.community}
        )
        # Wrap Django request with DRF Request to provide query_params
        request = Request(django_request)

        response = view.get(request)

        mock_get_sponsors.assert_called_once_with(
            community=self.community,
            sponsor_keyword=None
        )
        self.assertEqual(response.status_code, 200)

    @mock.patch('meeting.application.meeting.MeetingApp.get_meeting_sponsors')
    def test_get_sponsors_with_keyword(self, mock_get_sponsors):
        """Test GET with keyword filter."""
        mock_get_sponsors.return_value = ['Alice_Smith']

        view = MeetingSponsorView()
        django_request = self.factory.get(
            '/inner/sponsors/',
            {
                'community': self.community,
                'sponsor': 'Smith'
            }
        )
        # Wrap Django request with DRF Request to provide query_params
        request = Request(django_request)

        response = view.get(request)

        mock_get_sponsors.assert_called_once_with(
            community=self.community,
            sponsor_keyword='Smith'
        )
        self.assertEqual(response.status_code, 200)

    def test_get_sponsors_missing_community(self):
        """Test GET raises error when community is missing."""
        view = MeetingSponsorView()
        django_request = self.factory.get('/inner/sponsors/', {})
        # Wrap Django request with DRF Request to provide query_params
        request = Request(django_request)

        # MyValidationError is raised directly when community is missing
        from meeting_platform.utils.ret_api import MyValidationError
        with self.assertRaises(MyValidationError):
            view.get(request)


class MeetingParticipantsViewTest(TestCommonMeeting):
    """Test MeetingParticipantsView."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')
        self.user = self.create_user()
        self.enable_client_auth(self.user.username)

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.controller.inner.MeetingParticipantsView.app_class')
    def test_get_participants_success(self, mock_app_class):
        """Test retrieving meeting participants."""
        mock_app_class.get_participants.return_value = ['Alice', 'Bob']

        meeting = MeetingDao.create(
            sponsor="test_sponsor",
            group_name="test_group",
            community=self.community,
            topic="Test Meeting",
            platform="WELINK",
            is_cycle=False,
            date=self.today,
            start="10:00",
            end="11:00",
            is_record=False,
            mid=f"test_mid_{datetime.datetime.now().timestamp()}",
            host_id="test@example.com",
        )

        response = self.client.get(f'/inner/v1/meeting/meeting/participants/{meeting.id}/')

        mock_app_class.get_participants.assert_called_once_with(meeting.id)
        self.assertEqual(response.status_code, 200)


class MeetingPlatformViewTest(TestCommonMeeting):
    """Test MeetingPlatformView."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.user = self.create_user()
        self.enable_client_auth(self.user.username)

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.controller.inner.MeetingPlatformView.app_class')
    def test_get_platform_success(self, mock_app_class):
        """Test retrieving supported platforms."""
        mock_app_class.get_meeting_platform.return_value = ['welink', 'zoom']

        response = self.client.get('/inner/v1/meeting/meeting/platform/', {'community': self.community})

        mock_app_class.get_meeting_platform.assert_called_once_with(self.community)
        self.assertEqual(response.status_code, 200)


class MeetingGroupViewTest(TestCommonMeeting):
    """Test MeetingGroupView."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')
        self.user = self.create_user()
        self.enable_client_auth(self.user.username)

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.controller.inner.MeetingGroupView.app_class')
    def test_get_group_names_success(self, mock_app_class):
        """Test retrieving group names."""
        mock_app_class.get_meeting_group_name.return_value = ['group1', 'group2']

        # URL should be 'meeting/meeting/group_name/' not 'meeting/group/'
        response = self.client.get('/inner/v1/meeting/meeting/group_name/', {'community': self.community})

        mock_app_class.get_meeting_group_name.assert_called_once_with(self.community)
        self.assertEqual(response.status_code, 200)


class MeetingDateViewTest(TestCommonMeeting):
    """Test MeetingDateView."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')
        self.user = self.create_user()
        self.enable_client_auth(self.user.username)

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.controller.inner.MeetingDateView.app_class')
    def test_get_dates_success(self, mock_app_class):
        """Test retrieving meeting dates."""
        mock_app_class.get_meeting_date.return_value = []

        response = self.client.get('/inner/v1/meeting/meeting/date/', {
            'community': self.community,
            'date': self.today
        })

        mock_app_class.get_meeting_date.assert_called_once()
        self.assertEqual(response.status_code, 200)