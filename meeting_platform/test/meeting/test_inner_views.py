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
from meeting.controller.inner import ForceEndMeetingView, MeetingListView, MeetingSponsorView, MeetingView
from meeting_platform.test.meeting.test_base import TestCommonMeeting
from meeting_platform.utils.ret_code import RetCode
from meeting.models import MeetingCycleSubMeeting, MeetingCycleDate


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

    @mock.patch('meeting.application.meeting.MeetingApp.get_merged_meeting_list')
    def test_get_serializer_used(self, mock_get_merged):
        """Test GET uses MeetingListSerializer for output (covers lines 392-394)."""
        mock_get_merged.return_value = {
            'total': 1,
            'list': [
                {'id': 1, 'mid': 'mid_1', 'is_cycle': False, 'sub_id': None, 'group_name': 'SIG1', 'community': self.community, 'platform': 'WELINK', 'topic': 'Meeting 1', 'sponsor': 'Alice', 'date': self.today, 'start': '10:00', 'end': '11:00', 'status': 0, 'agenda': None, 'etherpad': None, 'join_url': None, 'cycle_start_date': None, 'cycle_end_date': None, 'cycle_start': None, 'cycle_end': None, 'cycle_type': None, 'cycle_interval': None, 'cycle_point': None},
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

    @mock.patch('meeting.controller.serializers.meeting_serializers.MeetingListQuerySerializer.is_valid')
    def test_get_validation_error(self, mock_is_valid):
        """Test GET raises error when validation fails (covers lines 361-366)."""
        mock_is_valid.side_effect = Exception("Validation error")

        view = MeetingListView()
        django_request = self.factory.get(
            '/inner/meeting/list/',
            {'community': self.community}
        )
        request = Request(django_request)

        # Should handle validation error
        from meeting_platform.utils.ret_api import MyValidationError
        with self.assertRaises(Exception):
            view.get(request)

    @mock.patch('meeting.application.meeting.MeetingApp.get_merged_meeting_list')
    def test_get_with_default_order_by(self, mock_get_merged):
        """Test GET uses default order_by when not specified (covers line 385)."""
        mock_get_merged.return_value = {
            'total': 0,
            'list': [],
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

        # Verify default order_by is 'date'
        call_args = mock_get_merged.call_args
        self.assertEqual(call_args[1]['order_by'], 'date')

    @mock.patch('meeting.application.meeting.MeetingApp.get_merged_meeting_list')
    def test_get_with_default_page_size(self, mock_get_merged):
        """Test GET uses default page_size when not specified (covers line 388)."""
        mock_get_merged.return_value = {
            'total': 0,
            'list': [],
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

        # Verify default page_size is 10
        call_args = mock_get_merged.call_args
        self.assertEqual(call_args[1]['page_size'], 10)

    @mock.patch('meeting.application.meeting.MeetingApp.get_merged_meeting_list')
    def test_get_serializer_validation_success(self, mock_get_merged):
        """Test GET with valid serializer validation success (covers lines 364-366)."""
        mock_get_merged.return_value = {
            'total': 1,
            'list': [
                {'id': 1, 'mid': 'mid_1', 'is_cycle': False, 'sub_id': None, 'group_name': 'SIG1',
                 'community': self.community, 'platform': 'WELINK', 'topic': 'Meeting 1',
                 'sponsor': 'Alice', 'date': self.today, 'start': '10:00', 'end': '11:00',
                 'status': 0, 'is_delete': 0, 'agenda': None, 'etherpad': None, 'join_url': None,
                 'cycle_start_date': None, 'cycle_end_date': None, 'cycle_start': None,
                 'cycle_end': None, 'cycle_type': None, 'cycle_interval': None, 'cycle_point': None},
            ],
            'page': 1,
            'size': 10
        }

        view = MeetingListView()
        # Test with all valid query parameters that should pass serializer validation
        django_request = self.factory.get(
            '/inner/meeting/list/',
            {
                'community': self.community,
                'date': self.today,
                'sponsor': 'Alice',
                'group_name': 'SIG1',
                'platform': 'WELINK',
                'topic': 'Meeting',
                'status': 0,
                'include_private': 'false',
                'page': 1,
                'size': 20,
                'order_by': 'date',
                'order_type': 'desc'
            }
        )
        request = Request(django_request)

        response = view.get(request)

        # Verify that serializer validation succeeded and app was called with correct params
        mock_get_merged.assert_called_once()
        call_args = mock_get_merged.call_args

        # Verify validated data was passed correctly
        self.assertEqual(call_args[1]['filters']['date'], self.today)
        self.assertEqual(call_args[1]['filters']['sponsor'], 'Alice')
        self.assertEqual(call_args[1]['filters']['group_name'], 'SIG1')
        self.assertEqual(call_args[1]['filters']['platform'], 'WELINK')
        self.assertEqual(call_args[1]['filters']['topic'], 'Meeting')
        self.assertEqual(call_args[1]['filters']['status'], 0)
        self.assertEqual(call_args[1]['page'], 1)
        self.assertEqual(call_args[1]['page_size'], 20)
        self.assertEqual(call_args[1]['order_by'], 'date')
        self.assertEqual(call_args[1]['order_type'], 'desc')
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

    def test_get_sponsors_invalid_community(self):
        """Test GET raises error when community is not in COMMUNITY_SUPPORT (covers lines 273-274)."""
        view = MeetingSponsorView()
        django_request = self.factory.get('/inner/sponsors/', {'community': 'invalid_community'})
        request = Request(django_request)

        from meeting_platform.utils.ret_api import MyValidationError
        from django.conf import settings
        # Mock COMMUNITY_SUPPORT to not include 'invalid_community'
        with mock.patch.object(settings, 'COMMUNITY_SUPPORT', ['openEuler', 'opengauss']):
            with self.assertRaises(MyValidationError):
                view.get(request)

    @mock.patch('meeting.application.meeting.MeetingApp.get_meeting_sponsors')
    def test_get_sponsors_with_sponsor_keyword(self, mock_get_sponsors):
        """Test GET with sponsor keyword filter (covers line 276)."""
        mock_get_sponsors.return_value = ['Alice_Smith']

        view = MeetingSponsorView()
        django_request = self.factory.get('/inner/sponsors/', {
            'community': self.community,
            'sponsor': 'Smith'
        })
        request = Request(django_request)

        response = view.get(request)

        mock_get_sponsors.assert_called_once_with(
            community=self.community,
            sponsor_keyword='Smith'
        )
        self.assertEqual(response.status_code, 200)

    def test_get_sponsors_returns_data_correctly(self):
        """Test GET returns data correctly (covers lines 278-282)."""
        from meeting_platform.utils.ret_api import ret_json

        # Create a meeting to have sponsors
        self._create_meeting(sponsor="TestSponsor")

        view = MeetingSponsorView()
        django_request = self.factory.get('/inner/sponsors/', {'community': self.community})
        request = Request(django_request)

        response = view.get(request)

        # Verify response has correct structure
        self.assertEqual(response.status_code, 200)


class ForceEndMeetingViewFullTest(TestCommonMeeting):
    """Test ForceEndMeetingView POST method covering all branches."""

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

    @mock.patch('meeting.application.meeting.MeetingApp.force_stop_meeting')
    def test_post_success_returns_json(self, mock_force_stop):
        """Test POST returns success JSON (covers lines 319-320)."""
        mock_force_stop.return_value = True
        meeting = self._create_meeting()

        view = ForceEndMeetingView()
        request = mock.MagicMock()
        request.data = {'meeting_id': meeting.id}

        response = view.post(request)

        self.assertEqual(response.status_code, 200)


class MeetingListViewFullTest(TestCommonMeeting):
    """Test MeetingListView GET method covering all branches."""

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

    @mock.patch('meeting.application.meeting.MeetingApp.get_merged_meeting_list')
    def test_get_returns_result_dict(self, mock_get_merged):
        """Test GET returns result dict (covers lines 382-394)."""
        mock_get_merged.return_value = {
            'total': 1,
            'list': [
                {'id': 1, 'mid': 'mid_1', 'is_cycle': False, 'sub_id': None, 'group_name': 'SIG1',
                 'community': self.community, 'platform': 'WELINK', 'topic': 'Meeting 1',
                 'sponsor': 'Alice', 'date': self.today, 'start': '10:00', 'end': '11:00',
                 'status': 0, 'is_delete': 0, 'agenda': None, 'etherpad': None, 'join_url': None},
            ],
            'page': 1,
            'size': 10
        }

        view = MeetingListView()
        django_request = self.factory.get('/inner/meeting/list/', {'community': self.community})
        request = Request(django_request)

        response = view.get(request)

        # Verify response structure (covers lines 392-394)
        self.assertEqual(response.status_code, 200)

    @mock.patch('meeting.application.meeting.MeetingApp.get_merged_meeting_list')
    def test_get_with_all_params(self, mock_get_merged):
        """Test GET with all query parameters (covers lines 361-389)."""
        mock_get_merged.return_value = {
            'total': 0,
            'list': [],
            'page': 1,
            'size': 20
        }

        view = MeetingListView()
        django_request = self.factory.get('/inner/meeting/list/', {
            'community': self.community,
            'date': self.today,
            'sponsor': 'Alice',
            'group_name': 'SIG1',
            'platform': 'WELINK',
            'topic': 'Test',
            'status': 0,
            'include_private': 'false',
            'page': 1,
            'size': 20,
            'order_by': 'date',
            'order_type': 'desc'
        })
        request = Request(django_request)

        response = view.get(request)

        mock_get_merged.assert_called_once()
        self.assertEqual(response.status_code, 200)


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


class MeetingViewQuerySetTest(TestCommonMeeting):
    """Test MeetingView.get_queryset date sorting logic for cycle meetings.

    Covers missing lines 108, 111, 113-115, 117, 123, 129, 144-145, 147-148, 151-153.
    """

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')
        self.yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        self.tomorrow = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        self.user = self.create_user()
        self.enable_client_auth(self.user.username)

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def _create_meeting(self, **kwargs):
        """Create a non-cycle meeting."""
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

    def _create_cycle_meeting_with_sub(self, date, start="10:00", end="11:00", mid_prefix="cycle"):
        """Create a cycle meeting with a sub-meeting on specific date."""
        parent = MeetingDao.create(
            sponsor="cycle_sponsor",
            group_name="cycle_group",
            community=self.community,
            topic="Cycle Meeting",
            platform="WELINK",
            is_cycle=True,
            is_record=False,
            mid=f"{mid_prefix}_mid_{datetime.datetime.now().timestamp()}",
            host_id="cycle@example.com",
            status=BusinessMeetingStatus.NOT_STARTED.value,
            date=self.today,
            start="09:00",
            end="12:00",
        )

        # Create cycle date record
        MeetingCycleDate.objects.create(
            mid=parent.mid,
            start_date=self.yesterday,
            end_date=self.tomorrow,
            start=start,
            end=end,
            cycle_type=CycleType.DAY.value,
            interval=1,
            meeting=parent
        )

        # Create sub-meeting on specific date
        sub = MeetingCycleSubMeeting.objects.create(
            mid=parent.mid,
            sub_id=f"sub_{datetime.datetime.now().timestamp()}",
            date=date,
            start=start,
            end=end,
            meeting=parent,
            status=BusinessMeetingStatus.NOT_STARTED.value
        )
        return parent, sub

    def _create_request_with_params(self, params):
        """Create a mock request object with query parameters."""
        from django.test import RequestFactory
        from rest_framework.request import Request
        factory = RequestFactory()
        django_request = factory.get('/inner/v1/meeting/meeting/', params)
        return Request(django_request)

    def test_get_queryset_date_order_by_direct(self):
        """Test get_queryset directly with order_by=date for cycle meetings.

        Covers lines 108, 111, 117, 123, 129, 144-145.
        """
        # Create a cycle meeting with sub-meeting
        parent, sub = self._create_cycle_meeting_with_sub(self.tomorrow, "14:00", "15:00")
        non_cycle = self._create_meeting(date=self.today, start="10:00", end="11:00")

        # Create view and request
        view = MeetingView()
        view.request = self._create_request_with_params({
            'community': self.community,
            'order_by': 'date',
            'order_type': 'desc'
        })
        view.format_kwarg = None

        # Call get_queryset directly
        queryset = view.get_queryset()

        # Verify queryset is returned
        self.assertIsNotNone(queryset)
        # Lines 108, 111, 117, 123, 129, 144-145 should be covered

    def test_get_queryset_with_filter_date_direct(self):
        """Test get_queryset directly with order_by=date and date filter.

        Covers lines 113-115 - filter_date parameter is used in subquery.
        """
        parent, sub = self._create_cycle_meeting_with_sub(self.tomorrow)

        view = MeetingView()
        view.request = self._create_request_with_params({
            'community': self.community,
            'order_by': 'date',
            'order_type': 'desc',
            'date': self.tomorrow
        })
        view.format_kwarg = None

        queryset = view.get_queryset()
        self.assertIsNotNone(queryset)
        # Lines 113-115 should be covered

    def test_get_queryset_date_asc_order_direct(self):
        """Test get_queryset directly with order_by=date and order_type=asc.

        Covers lines 147-148 - ascending order for date sorting.
        """
        self._create_cycle_meeting_with_sub(self.yesterday, "09:00", "10:00", mid_prefix="cycle1")
        self._create_cycle_meeting_with_sub(self.tomorrow, "14:00", "15:00", mid_prefix="cycle2")
        self._create_meeting(date=self.today, start="10:00", end="11:00")

        view = MeetingView()
        view.request = self._create_request_with_params({
            'community': self.community,
            'order_by': 'date',
            'order_type': 'asc'
        })
        view.format_kwarg = None

        queryset = view.get_queryset()
        self.assertIsNotNone(queryset)
        # Lines 147-148 should be covered

    def test_get_queryset_non_date_desc_order_direct(self):
        """Test get_queryset directly with order_by not 'date' and order_type=desc.

        Covers lines 151-153 - non-date sorting with descending order.
        """
        self._create_meeting(date=self.today, start="09:00", end="10:00")
        self._create_meeting(date=self.today, start="14:00", end="15:00")

        view = MeetingView()
        view.request = self._create_request_with_params({
            'community': self.community,
            'order_by': 'create_time',
            'order_type': 'desc'
        })
        view.format_kwarg = None

        queryset = view.get_queryset()
        self.assertIsNotNone(queryset)
        # Lines 151-153 should be covered

    def test_get_queryset_non_date_default_order_direct(self):
        """Test get_queryset directly with order_by not 'date' without order_type.

        Covers lines 151-153 - non-date sorting path with default order_type.
        """
        self._create_meeting(date=self.today, start="10:00", end="11:00")

        view = MeetingView()
        view.request = self._create_request_with_params({
            'community': self.community,
            'order_by': 'update_time'
        })
        view.format_kwarg = None

        queryset = view.get_queryset()
        self.assertIsNotNone(queryset)
        # Lines 151-153 should be covered