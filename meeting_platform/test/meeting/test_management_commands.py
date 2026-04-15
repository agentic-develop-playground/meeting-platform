#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
"""
Unit tests for management commands.

Tests include:
- handle_meeting.py - static method tests
- handle_recordings.py - static method tests that don't require initialization
"""
import datetime
from unittest import mock

from django.test import override_settings

from meeting.management.commands.handle_meeting import HandleMeeting
from meeting.management.commands.handle_recordings import HandleRecording
from meeting_platform.test.meeting.test_base import TestCommonMeeting


class HandleMeetingStaticMethodTest(TestCommonMeeting):
    """Test handle_meeting.py static methods."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def test_get_windows_meeting_time_calculation(self):
        """Test _get_windows_meeting calculates time window correctly."""
        result = HandleMeeting._get_windows_meeting()

        # Should return tuple of three strings
        self.assertEqual(len(result), 3)
        today_date, start_time, end_time = result

        # Verify date format
        self.assertEqual(today_date, datetime.datetime.now().strftime('%Y-%m-%d'))

        # Verify time format (HH:MM)
        self.assertRegex(start_time, r'^\d{2}:\d{2}$')
        self.assertRegex(end_time, r'^\d{2}:\d{2}$')

    def test_get_point_meeting_date_calculation(self):
        """Test _get_point_meeting calculates date range correctly."""
        result = HandleMeeting._get_point_meeting()

        # Should return tuple of two strings
        self.assertEqual(len(result), 2)
        start_date, end_date = result

        # Verify date format
        self.assertRegex(start_date, r'^\d{4}-\d{2}-\d{2}$')
        self.assertRegex(end_date, r'^\d{4}-\d{2}-\d{2}$')

    def test_get_windows_meeting_returns_today(self):
        """Test _get_windows_meeting returns today's date."""
        result = HandleMeeting._get_windows_meeting()
        today = datetime.datetime.now().strftime('%Y-%m-%d')
        self.assertEqual(result[0], today)


class HandleRecordingsStaticMethodTest(TestCommonMeeting):
    """Test handle_recordings.py static methods that don't require instance."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def test_cover_content_formatting(self):
        """Test _cover_content generates correct HTML template."""
        # The _cover_content is decorated with @staticmethod, call it directly
        content = HandleRecording._cover_content(
            topic="Test Topic",
            group_name="Test SIG",
            date="2026-04-14",
            start_time="10:00",
            end_time="11:00"
        )

        # Verify HTML structure
        self.assertIn("<!DOCTYPE html>", content)
        self.assertIn("Test Topic", content)
        self.assertIn("Test SIG", content)
        self.assertIn("2026-04-14", content)
        self.assertIn("10:00-11:00", content)

    def test_cover_content_static(self):
        """Test _cover_content as static method directly."""
        # The _cover_content is decorated with @staticmethod
        content = HandleRecording._cover_content(
            topic="Static Test",
            group_name="Static SIG",
            date="2026-04-15",
            start_time="14:00",
            end_time="15:00"
        )

        self.assertIn("Static Test", content)
        self.assertIn("Static SIG", content)
        self.assertIn("2026-04-15", content)
        self.assertIn("14:00-15:00", content)

    def test_manual_url_encode_encodes_chinese(self):
        """Test _manual_url_encode properly encodes Chinese characters."""
        text = "测试中文"
        result = HandleRecording._manual_url_encode(text)

        # Should be URL encoded
        self.assertNotEqual(result, text)
        self.assertIn("%", result)  # URL encoded characters contain %

    def test_manual_url_encode_preserves_safe_chars(self):
        """Test _manual_url_encode preserves safe characters."""
        text = "SIG-test_123"
        result = HandleRecording._manual_url_encode(text)

        # Safe characters should not be encoded
        self.assertEqual(result, text)

    def test_manual_url_encode_preserves_letters_digits(self):
        """Test _manual_url_encode preserves alphanumeric characters."""
        text = "abcdef123456"
        result = HandleRecording._manual_url_encode(text)
        self.assertEqual(result, text)

    def test_manual_url_encode_preserves_dash_underscore_dot_tilde(self):
        """Test _manual_url_encode preserves -, _, ., ~ characters."""
        text = "test-file_name.v1~beta"
        result = HandleRecording._manual_url_encode(text)
        self.assertEqual(result, text)

    def test_get_valid_query_range_returns_tuple(self):
        """Test _get_valid_query_range returns correct tuple."""
        result = HandleRecording._get_valid_query_range()

        # Should return tuple of two strings
        self.assertEqual(len(result), 2)
        start_date, end_date = result

        # Verify date format
        self.assertRegex(start_date, r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$')
        self.assertRegex(end_date, r'^\d{4}-\d{2}-\d{2}$')


class HandleMeetingCommandTest(TestCommonMeeting):
    """Test handle_meeting.py command behavior."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def test_handle_meeting_class_attrs(self):
        """Test HandleMeeting class attributes."""
        handler = HandleMeeting(self.community)

        # Verify class attributes exist
        self.assertIsNotNone(handler.meeting_dao)
        self.assertIsNotNone(handler.meeting_adapter_impl)

    def test_handle_meeting_init_sets_community(self):
        """Test HandleMeeting.__init__ sets community correctly."""
        handler = HandleMeeting(self.community)
        self.assertEqual(handler.community, self.community)


class HandleMeetingForceStopTest(TestCommonMeeting):
    """Test HandleMeeting.force_stop_meeting method."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.management.commands.handle_meeting.HandleMeeting._get_cur_day_meeting')
    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.force_end_meeting')
    @override_settings(CRONJOB_FORCE_END_MEETING=True, HANDLE_MEETING_SCHEDULE_PLAN='windows')
    def test_force_stop_meeting_windows_mode(self, mock_force_end, mock_get_meetings):
        """Test force_stop_meeting in windows mode."""
        handler = HandleMeeting(self.community)

        # Mock meeting data
        mock_meeting = mock.MagicMock()
        mock_meeting.id = 1
        mock_meeting.mid = "test_mid"
        mock_get_meetings.return_value = [mock_meeting]

        handler.force_stop_meeting()

        mock_force_end.assert_called()

    @mock.patch('meeting.management.commands.handle_meeting.HandleMeeting._get_cur_day_meeting')
    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.force_end_meeting')
    @override_settings(CRONJOB_FORCE_END_MEETING=True, HANDLE_MEETING_SCHEDULE_PLAN='point')
    def test_force_stop_meeting_point_mode(self, mock_force_end, mock_get_meetings):
        """Test force_stop_meeting in point mode."""
        handler = HandleMeeting(self.community)

        mock_meeting = mock.MagicMock()
        mock_meeting.id = 1
        mock_get_meetings.return_value = [mock_meeting]

        handler.force_stop_meeting()

        mock_force_end.assert_called()


class HandleMeetingRefreshTest(TestCommonMeeting):
    """Test HandleMeeting.refresh_meeting_participants method."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.management.commands.handle_meeting.model_to_dict')
    @mock.patch('meeting.management.commands.handle_meeting.HandleMeeting._get_cur_day_meeting')
    @mock.patch('meeting.infrastructure.dao.meeting_participants_dao.MeetingParticipantsDao.get')
    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.get_participants')
    @mock.patch('meeting.infrastructure.dao.meeting_participants_dao.MeetingParticipantsDao.create')
    def test_refresh_meeting_participants(self, mock_create, mock_get_participants, mock_dao_get, mock_get_meetings, mock_model_to_dict):
        """Test refresh_meeting_participants creates participant records."""
        handler = HandleMeeting(self.community)

        # Mock meeting without existing participant record
        mock_meeting = mock.MagicMock()
        mock_meeting.id = 1
        mock_meeting.mid = "test_mid"
        mock_get_meetings.return_value = [mock_meeting]

        # No existing participant record
        mock_dao_get.return_value = None

        # Mock model_to_dict to return proper dictionary
        mock_model_to_dict.return_value = {
            'id': 1,
            'mid': 'test_mid',
            'is_cycle': False,
            'sponsor': 'test_sponsor',
            'group_name': 'test_group',
            'topic': 'Test Meeting',
            'date': self.today,
            'start': '10:00',
            'end': '11:00',
            'community': self.community,
            'platform': 'WELINK',
            'is_record': False,
            'is_delete': 0,
            'status': 0,
            'sequence': 0,
            'is_private': False,
            'emergency': False,
            'agenda': '',
            'mid_url': '',
            'join_url': '',
            'host_id': 'test@example.com'
        }

        # Mock participant data from adapter
        mock_get_participants.return_value = {
            'participants': [
                {'name': 'Alice'},
                {'name': 'Bob'}
            ]
        }

        handler.refresh_meeting_participants()

        # Should create participant record
        mock_create.assert_called()


class HandleRecordingUploadObsTest(TestCommonMeeting):
    """Test HandleRecording.upload_obs method."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.management.commands.handle_recordings.BiliAdapterImpl')
    @mock.patch('meeting.management.commands.handle_recordings.TranslateAdapterImpl')
    @mock.patch('meeting.infrastructure.dao.meeting_records_obs_dao.MeetingRecordsObsDao.get_records_by_status')
    @mock.patch('meeting.infrastructure.dao.meeting_dao.MeetingDao.get_meeting_by_obs_records')
    @mock.patch('meeting.management.commands.handle_recordings.HandleRecording._get_video_path')
    @mock.patch('meeting.management.commands.handle_recordings.HandleRecording._get_video_cover_path')
    def test_upload_obs_video_path_not_exists(self, mock_cover_path, mock_video_path, mock_get_meetings, mock_get_records, mock_translate, mock_bili):
        """Test upload_obs handles non-existent video path."""
        mock_translate.return_value = mock.MagicMock()
        mock_bili.return_value = mock.MagicMock()
        handler = HandleRecording(self.community)

        # Mock records and meetings
        mock_record = mock.MagicMock()
        mock_record.meeting_id = 1
        mock_get_records.return_value = [mock_record]

        mock_meeting = mock.MagicMock()
        mock_meeting.is_private = False
        mock_meeting.is_cycle = False
        mock_meeting.id = 1
        mock_meeting.mid = "test_mid"
        mock_meeting.group_name = "test_group"
        mock_meeting.topic = "Test Meeting"
        mock_meeting.date = self.today
        mock_meeting.start = "10:00"
        mock_meeting.end = "11:00"
        mock_meeting.community = self.community
        mock_meeting.sponsor = "test_sponsor"
        mock_meeting.agenda = ""
        mock_get_meetings.return_value = [mock_meeting]

        # Video path returns None (doesn't exist)
        mock_video_path.return_value = None

        result = handler.upload_obs()

        # Should return empty cache when video path is None
        self.assertIsInstance(result, dict)

    @mock.patch('meeting.management.commands.handle_recordings.BiliAdapterImpl')
    @mock.patch('meeting.management.commands.handle_recordings.TranslateAdapterImpl')
    @mock.patch('meeting.infrastructure.dao.meeting_records_obs_dao.MeetingRecordsObsDao.get_records_by_status')
    def test_upload_obs_success(self, mock_get_records, mock_translate, mock_bili):
        """Test upload_obs processes records successfully."""
        mock_translate.return_value = mock.MagicMock()
        mock_bili.return_value = mock.MagicMock()
        handler = HandleRecording(self.community)

        # Mock empty records (no work to do)
        mock_get_records.return_value = []

        result = handler.upload_obs()

        # Should return empty dict when no records
        self.assertEqual(result, {})


class HandleRecordingUploadBiliTest(TestCommonMeeting):
    """Test HandleRecording.upload_bili method."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.management.commands.handle_recordings.BiliAdapterImpl')
    @mock.patch('meeting.management.commands.handle_recordings.TranslateAdapterImpl')
    @mock.patch('meeting.infrastructure.dao.meeting_records_bili_dao.MeetingRecordsBiliDao.get_records_by_status')
    @mock.patch('meeting.infrastructure.dao.meeting_dao.MeetingDao.get_meeting_by_bili_records')
    def test_upload_bili_private_meeting_skip(self, mock_get_meetings, mock_get_records, mock_translate, mock_bili):
        """Test upload_bili skips private meetings."""
        mock_translate.return_value = mock.MagicMock()
        mock_bili.return_value = mock.MagicMock()
        handler = HandleRecording(self.community)

        # Mock records
        mock_record = mock.MagicMock()
        mock_record.meeting_id = 1
        mock_get_records.return_value = [mock_record]

        # Mock private meeting
        mock_meeting = mock.MagicMock()
        mock_meeting.is_private = True
        mock_meeting.is_cycle = False
        mock_meeting.id = 1
        mock_meeting.mid = "test_mid"
        mock_meeting.group_name = "test_group"
        mock_meeting.topic = "Test Meeting"
        mock_meeting.date = self.today
        mock_meeting.start = "10:00"
        mock_meeting.end = "11:00"
        mock_meeting.community = self.community
        mock_meeting.sponsor = "test_sponsor"
        mock_meeting.agenda = ""
        mock_get_meetings.return_value = [mock_meeting]

        # Call upload_bili with empty cache_path
        handler.upload_bili({})

        # Meeting should be skipped due to is_private

    @mock.patch('meeting.management.commands.handle_recordings.BiliAdapterImpl')
    @mock.patch('meeting.management.commands.handle_recordings.TranslateAdapterImpl')
    @mock.patch('meeting.infrastructure.dao.meeting_records_bili_dao.MeetingRecordsBiliDao.get_records_by_status')
    def test_upload_bili_success(self, mock_get_records, mock_translate, mock_bili):
        """Test upload_bili processes records successfully."""
        mock_translate.return_value = mock.MagicMock()
        mock_bili.return_value = mock.MagicMock()
        handler = HandleRecording(self.community)

        # Mock empty records
        mock_get_records.return_value = []

        # Should not raise any errors with empty records
        handler.upload_bili({})


class WorkFlowTest(TestCommonMeeting):
    """Test work_flow function."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.management.commands.handle_recordings.BiliAdapterImpl')
    @mock.patch('meeting.management.commands.handle_recordings.TranslateAdapterImpl')
    @override_settings(IS_UPLOAD_OBS=False, IS_UPLOAD_BILI=False)
    def test_workflow_skips_uploads_when_disabled(self, mock_translate, mock_bili):
        """Test work_flow skips uploads when settings disabled."""
        mock_translate.return_value = mock.MagicMock()
        mock_bili.return_value = mock.MagicMock()
        from meeting.management.commands.handle_recordings import work_flow

        handler = HandleRecording(self.community)
        work_flow(handler)

        # Should complete without errors

    @override_settings(CRONJOB_FORCE_END_MEETING=False)
    def test_handle_meeting_workflow_skips_force_end(self):
        """Test work_flow skips force_end when setting disabled."""
        from meeting.management.commands.handle_meeting import work_flow

        handler = HandleMeeting(self.community)
        work_flow(handler)

        # Should complete without errors


class HandleMeetingSchedulePlanTest(TestCommonMeeting):
    """Test MeetingSchedulePlan enum."""

    def setUp(self):
        super().setUp()

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @override_settings(HANDLE_MEETING_SCHEDULE_PLAN='windows')
    def test_from_settings_windows(self):
        """Test from_settings returns WINDOWS when configured."""
        from meeting.management.commands.handle_meeting import MeetingSchedulePlan

        result = MeetingSchedulePlan.from_settings()
        self.assertEqual(result, MeetingSchedulePlan.WINDOWS)

    @override_settings(HANDLE_MEETING_SCHEDULE_PLAN='point')
    def test_from_settings_point(self):
        """Test from_settings returns DEFAULT when configured as point."""
        from meeting.management.commands.handle_meeting import MeetingSchedulePlan

        result = MeetingSchedulePlan.from_settings()
        self.assertEqual(result, MeetingSchedulePlan.DEFAULT)

    @override_settings(HANDLE_MEETING_SCHEDULE_PLAN='unknown')
    def test_from_settings_unknown_returns_default(self):
        """Test from_settings returns DEFAULT for unknown value."""
        from meeting.management.commands.handle_meeting import MeetingSchedulePlan

        result = MeetingSchedulePlan.from_settings()
        self.assertEqual(result, MeetingSchedulePlan.DEFAULT)


class HandleMeetingStatusCalculateStatusTest(TestCommonMeeting):
    """Test HandleMeetingStatus._calculate_status static method."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.now = datetime.datetime.now()

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def test_calculate_status_no_date_returns_not_started(self):
        """Test _calculate_status returns NOT_STARTED when date is None."""
        from meeting.management.commands.handle_meeting_status import HandleMeetingStatus
        from meeting.domain.primitive.meeting_status import BusinessMeetingStatus

        result = HandleMeetingStatus._calculate_status(None, "10:00", "11:00", False, self.now)
        self.assertEqual(result, BusinessMeetingStatus.NOT_STARTED.value)

    def test_calculate_status_no_start_returns_not_started(self):
        """Test _calculate_status returns NOT_STARTED when start is None."""
        from meeting.management.commands.handle_meeting_status import HandleMeetingStatus
        from meeting.domain.primitive.meeting_status import BusinessMeetingStatus

        result = HandleMeetingStatus._calculate_status("2026-04-15", None, "11:00", False, self.now)
        self.assertEqual(result, BusinessMeetingStatus.NOT_STARTED.value)

    def test_calculate_status_no_end_returns_not_started(self):
        """Test _calculate_status returns NOT_STARTED when end is None."""
        from meeting.management.commands.handle_meeting_status import HandleMeetingStatus
        from meeting.domain.primitive.meeting_status import BusinessMeetingStatus

        result = HandleMeetingStatus._calculate_status("2026-04-15", "10:00", None, False, self.now)
        self.assertEqual(result, BusinessMeetingStatus.NOT_STARTED.value)

    def test_calculate_status_invalid_date_format_returns_not_started(self):
        """Test _calculate_status returns NOT_STARTED for invalid date format."""
        from meeting.management.commands.handle_meeting_status import HandleMeetingStatus
        from meeting.domain.primitive.meeting_status import BusinessMeetingStatus

        result = HandleMeetingStatus._calculate_status("invalid", "10:00", "11:00", False, self.now)
        self.assertEqual(result, BusinessMeetingStatus.NOT_STARTED.value)

    def test_calculate_status_invalid_time_format_returns_not_started(self):
        """Test _calculate_status returns NOT_STARTED for invalid time format."""
        from meeting.management.commands.handle_meeting_status import HandleMeetingStatus
        from meeting.domain.primitive.meeting_status import BusinessMeetingStatus

        result = HandleMeetingStatus._calculate_status("2026-04-15", "invalid", "11:00", False, self.now)
        self.assertEqual(result, BusinessMeetingStatus.NOT_STARTED.value)

    def test_calculate_status_api_ongoing_before_end_returns_ongoing(self):
        """Test _calculate_status returns ONGOING when API reports ongoing before end time."""
        from meeting.management.commands.handle_meeting_status import HandleMeetingStatus
        from meeting.domain.primitive.meeting_status import BusinessMeetingStatus

        # Meeting is ongoing according to API, current time before end
        meeting_date = self.now.strftime('%Y-%m-%d')
        start_time = (self.now - datetime.timedelta(hours=1)).strftime('%H:%M')
        end_time = (self.now + datetime.timedelta(hours=1)).strftime('%H:%M')

        result = HandleMeetingStatus._calculate_status(meeting_date, start_time, end_time, True, self.now)
        self.assertEqual(result, BusinessMeetingStatus.ONGOING.value)

    def test_calculate_status_api_ongoing_after_end_returns_overtime(self):
        """Test _calculate_status returns OVERTIME when API reports ongoing after end time."""
        from meeting.management.commands.handle_meeting_status import HandleMeetingStatus
        from meeting.domain.primitive.meeting_status import BusinessMeetingStatus

        # Meeting is ongoing according to API, but current time is after end
        meeting_date = self.now.strftime('%Y-%m-%d')
        start_time = (self.now - datetime.timedelta(hours=2)).strftime('%H:%M')
        end_time = (self.now - datetime.timedelta(hours=1)).strftime('%H:%M')

        result = HandleMeetingStatus._calculate_status(meeting_date, start_time, end_time, True, self.now)
        self.assertEqual(result, BusinessMeetingStatus.OVERTIME.value)

    def test_calculate_status_before_start_returns_not_started(self):
        """Test _calculate_status returns NOT_STARTED when current time before start."""
        from meeting.management.commands.handle_meeting_status import HandleMeetingStatus
        from meeting.domain.primitive.meeting_status import BusinessMeetingStatus

        # Meeting hasn't started yet
        meeting_date = self.now.strftime('%Y-%m-%d')
        start_time = (self.now + datetime.timedelta(hours=1)).strftime('%H:%M')
        end_time = (self.now + datetime.timedelta(hours=2)).strftime('%H:%M')

        result = HandleMeetingStatus._calculate_status(meeting_date, start_time, end_time, False, self.now)
        self.assertEqual(result, BusinessMeetingStatus.NOT_STARTED.value)

    def test_calculate_status_during_meeting_returns_ongoing(self):
        """Test _calculate_status returns ONGOING when current time during meeting."""
        from meeting.management.commands.handle_meeting_status import HandleMeetingStatus
        from meeting.domain.primitive.meeting_status import BusinessMeetingStatus

        # Current time is during meeting time
        meeting_date = self.now.strftime('%Y-%m-%d')
        start_time = (self.now - datetime.timedelta(minutes=30)).strftime('%H:%M')
        end_time = (self.now + datetime.timedelta(minutes=30)).strftime('%H:%M')

        result = HandleMeetingStatus._calculate_status(meeting_date, start_time, end_time, False, self.now)
        self.assertEqual(result, BusinessMeetingStatus.ONGOING.value)

    def test_calculate_status_after_end_returns_ended(self):
        """Test _calculate_status returns ENDED when current time after end."""
        from meeting.management.commands.handle_meeting_status import HandleMeetingStatus
        from meeting.domain.primitive.meeting_status import BusinessMeetingStatus

        # Meeting has ended
        meeting_date = self.now.strftime('%Y-%m-%d')
        start_time = (self.now - datetime.timedelta(hours=2)).strftime('%H:%M')
        end_time = (self.now - datetime.timedelta(hours=1)).strftime('%H:%M')

        result = HandleMeetingStatus._calculate_status(meeting_date, start_time, end_time, False, self.now)
        self.assertEqual(result, BusinessMeetingStatus.ENDED.value)


class HandleMeetingStatusShouldSendWarningTest(TestCommonMeeting):
    """Test HandleMeetingStatus._should_send_warning static method."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.now = datetime.datetime.now()

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @override_settings(OVER_TIME_WARNING_ADVANCE_TIME=30)
    def test_should_send_warning_within_tolerance(self):
        """Test _should_send_warning returns True when within tolerance."""
        from meeting.management.commands.handle_meeting_status import HandleMeetingStatus

        # Set next meeting start time to be exactly 30 minutes from now (warning time)
        next_start = (self.now + datetime.timedelta(minutes=30)).strftime('%H:%M')

        result = HandleMeetingStatus._should_send_warning(next_start, self.now)
        self.assertTrue(result)

    @override_settings(OVER_TIME_WARNING_ADVANCE_TIME=30)
    def test_should_send_warning_outside_tolerance(self):
        """Test _should_send_warning returns False when outside tolerance."""
        from meeting.management.commands.handle_meeting_status import HandleMeetingStatus

        # Set next meeting start time to be 60 minutes from now (outside tolerance)
        next_start = (self.now + datetime.timedelta(minutes=60)).strftime('%H:%M')

        result = HandleMeetingStatus._should_send_warning(next_start, self.now)
        self.assertFalse(result)

    @override_settings(OVER_TIME_WARNING_ADVANCE_TIME=30)
    def test_should_send_warning_invalid_time_format(self):
        """Test _should_send_warning returns False for invalid time format."""
        from meeting.management.commands.handle_meeting_status import HandleMeetingStatus

        result = HandleMeetingStatus._should_send_warning("invalid", self.now)
        self.assertFalse(result)


class HandleMeetingStatusSyncTest(TestCommonMeeting):
    """Test HandleMeetingStatus.sync_meeting_status method."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.now = datetime.datetime.now()
        self.today = self.now.strftime('%Y-%m-%d')

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.management.commands.handle_meeting_status.MeetingAdapterImpl')
    @mock.patch('meeting.infrastructure.dao.meeting_dao.MeetingDao.get_status_sync_candidates')
    def test_sync_meeting_status_empty_meetings(self, mock_get_candidates, mock_adapter):
        """Test sync_meeting_status handles empty meeting list."""
        from meeting.management.commands.handle_meeting_status import HandleMeetingStatus

        mock_adapter.return_value = mock.MagicMock()
        mock_get_candidates.return_value = []

        handler = HandleMeetingStatus(self.community)
        handler.sync_meeting_status()

        # Should complete without errors
        mock_get_candidates.assert_called_once_with(self.community, mock.ANY)

    @mock.patch('meeting.management.commands.handle_meeting_status.HandleMeetingStatus.meeting_adapter_impl')
    @mock.patch('meeting.infrastructure.dao.meeting_dao.MeetingDao.get_status_sync_candidates')
    @mock.patch('meeting.infrastructure.dao.meeting_dao.MeetingDao.update_status')
    @mock.patch('meeting.management.commands.handle_meeting_status.model_to_dict')
    def test_sync_meeting_status_non_cycle_meeting(self, mock_model_to_dict, mock_update_status, mock_get_candidates, mock_adapter):
        """Test sync_meeting_status updates non-cycle meeting status."""
        from meeting.management.commands.handle_meeting_status import HandleMeetingStatus
        from meeting.domain.primitive.meeting_status import BusinessMeetingStatus

        # Mock adapter's get_meeting_status method
        mock_adapter.get_meeting_status.return_value = True

        # Mock meeting
        mock_meeting = mock.MagicMock()
        mock_meeting.is_cycle = False
        mock_meeting.status = BusinessMeetingStatus.NOT_STARTED.value
        mock_meeting.date = self.today
        mock_meeting.start = (self.now - datetime.timedelta(hours=1)).strftime('%H:%M')
        mock_meeting.end = (self.now + datetime.timedelta(hours=1)).strftime('%H:%M')
        mock_meeting.id = 1
        mock_meeting.mid = "test_mid"
        mock_get_candidates.return_value = [mock_meeting]

        mock_model_to_dict.return_value = {
            'id': 1,
            'mid': 'test_mid',
            'is_cycle': False,
            'date': self.today,
            'start': mock_meeting.start,
            'end': mock_meeting.end,
            'platform': 'WELINK',
            'community': self.community,
            'host_id': 'test@example.com',
        }

        handler = HandleMeetingStatus(self.community)
        handler.meeting_adapter_impl = mock_adapter
        handler.sync_meeting_status()

        # Should update status when changed
        mock_update_status.assert_called()


class HandleMeetingStatusWarningEmailTest(TestCommonMeeting):
    """Test HandleMeetingStatus.send_warning_emails method."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.now = datetime.datetime.now()
        self.today = self.now.strftime('%Y-%m-%d')

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @override_settings(OPERATOR_EMAILS={'openEuler': []})
    def test_send_warning_emails_no_operator_emails(self):
        """Test send_warning_emails handles no operator emails configured."""
        from meeting.management.commands.handle_meeting_status import HandleMeetingStatus

        handler = HandleMeetingStatus(self.community)
        handler.send_warning_emails()

        # Should complete without errors when no emails configured

    @mock.patch('meeting.infrastructure.dao.meeting_dao.MeetingDao.get_ongoing_meetings_for_warning')
    @mock.patch('meeting.infrastructure.dao.meeting_cycle_sub_dao.MeetingCycleSubMeetingDao.get_ongoing_sub_meetings_for_warning')
    @mock.patch('meeting.infrastructure.adapter.message_adapter_impl.email_adapter_impl.EmailAdapter')
    @override_settings(OPERATOR_EMAILS={'openEuler': ['operator@test.com']})
    def test_send_warning_emails_empty_ongoing_meetings(self, mock_email_adapter, mock_sub_dao, mock_meeting_dao):
        """Test send_warning_emails handles empty ongoing meetings list."""
        from meeting.management.commands.handle_meeting_status import HandleMeetingStatus

        mock_email_adapter.return_value = mock.MagicMock()
        mock_meeting_dao.return_value = []
        mock_sub_dao.return_value = []

        handler = HandleMeetingStatus(self.community)
        handler.send_warning_emails()

        # Should complete without errors


class HandleMeetingStatusGetNextMeetingTest(TestCommonMeeting):
    """Test HandleMeetingStatus._get_next_meeting_start_time method."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.infrastructure.dao.meeting_dao.MeetingDao.get_next_meeting_start_time')
    @mock.patch('meeting.infrastructure.dao.meeting_cycle_sub_dao.MeetingCycleSubMeetingDao.get_next_sub_meeting_start_time')
    def test_get_next_meeting_start_time_no_meetings(self, mock_sub_dao, mock_meeting_dao):
        """Test _get_next_meeting_start_time returns None when no meetings."""
        from meeting.management.commands.handle_meeting_status import HandleMeetingStatus

        mock_meeting_dao.return_value = None
        mock_sub_dao.return_value = None

        handler = HandleMeetingStatus(self.community)
        result = handler._get_next_meeting_start_time("host@test.com", self.today, "11:00")

        self.assertIsNone(result)

    @mock.patch('meeting.infrastructure.dao.meeting_dao.MeetingDao.get_next_meeting_start_time')
    @mock.patch('meeting.infrastructure.dao.meeting_cycle_sub_dao.MeetingCycleSubMeetingDao.get_next_sub_meeting_start_time')
    def test_get_next_meeting_start_time_returns_earliest(self, mock_sub_dao, mock_meeting_dao):
        """Test _get_next_meeting_start_time returns earliest meeting."""
        from meeting.management.commands.handle_meeting_status import HandleMeetingStatus

        mock_meeting_dao.return_value = "12:00"
        mock_sub_dao.return_value = "11:30"

        handler = HandleMeetingStatus(self.community)
        result = handler._get_next_meeting_start_time("host@test.com", self.today, "11:00")

        # Should return earliest time
        self.assertEqual(result, "11:30")

    @mock.patch('meeting.infrastructure.dao.meeting_dao.MeetingDao.get_next_meeting_start_time')
    @mock.patch('meeting.infrastructure.dao.meeting_cycle_sub_dao.MeetingCycleSubMeetingDao.get_next_sub_meeting_start_time')
    def test_get_next_meeting_start_time_only_non_cycle(self, mock_sub_dao, mock_meeting_dao):
        """Test _get_next_meeting_start_time with only non-cycle meeting."""
        from meeting.management.commands.handle_meeting_status import HandleMeetingStatus

        mock_meeting_dao.return_value = "14:00"
        mock_sub_dao.return_value = None

        handler = HandleMeetingStatus(self.community)
        result = handler._get_next_meeting_start_time("host@test.com", self.today, "11:00")

        self.assertEqual(result, "14:00")


class HandleMeetingStatusWorkflowTest(TestCommonMeeting):
    """Test handle_meeting_status work_flow function."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.management.commands.handle_meeting_status.HandleMeetingStatus.sync_meeting_status')
    @mock.patch('meeting.management.commands.handle_meeting_status.HandleMeetingStatus.send_warning_emails')
    def test_workflow_calls_both_methods(self, mock_send_warning, mock_sync_status):
        """Test work_flow calls both sync and warning methods."""
        from meeting.management.commands.handle_meeting_status import HandleMeetingStatus, work_flow

        handler = HandleMeetingStatus(self.community)
        work_flow(handler)

        mock_sync_status.assert_called_once()
        mock_send_warning.assert_called_once()


class HandleRecordingInitTest(TestCommonMeeting):
    """Test HandleRecording initialization."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.management.commands.handle_recordings.BiliAdapterImpl')
    @mock.patch('meeting.management.commands.handle_recordings.TranslateAdapterImpl')
    def test_init_sets_community(self, mock_translate, mock_bili):
        """Test HandleRecording.__init__ sets community."""
        mock_translate.return_value = mock.MagicMock()
        mock_bili.return_value = mock.MagicMock()
        handler = HandleRecording(self.community)
        self.assertEqual(handler.community, self.community)

    @mock.patch('meeting.management.commands.handle_recordings.BiliAdapterImpl')
    @mock.patch('meeting.management.commands.handle_recordings.TranslateAdapterImpl')
    def test_init_creates_adapters(self, mock_translate, mock_bili):
        """Test HandleRecording.__init__ creates adapters."""
        mock_translate.return_value = mock.MagicMock()
        mock_bili.return_value = mock.MagicMock()
        handler = HandleRecording(self.community)
        self.assertIsNotNone(handler.translate_adapter_impl)
        self.assertIsNotNone(handler.meeting_adapter_impl)
        self.assertIsNotNone(handler.bili_adapter_impl)


class HandleRecordingGetVideoPathTest(TestCommonMeeting):
    """Test HandleRecording._get_video_path method."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.management.commands.handle_recordings.BiliAdapterImpl')
    @mock.patch('meeting.management.commands.handle_recordings.TranslateAdapterImpl')
    def test_get_video_path_returns_none_when_empty(self, mock_translate, mock_bili):
        """Test _get_video_path returns None when adapter returns empty."""
        mock_translate.return_value = mock.MagicMock()
        mock_bili.return_value = mock.MagicMock()

        handler = HandleRecording(self.community)
        handler.meeting_adapter_impl.get_video = mock.MagicMock(return_value=None)

        result = handler._get_video_path({'mid': 'test_mid'})

        self.assertIsNone(result)

    @mock.patch('meeting.management.commands.handle_recordings.BiliAdapterImpl')
    @mock.patch('meeting.management.commands.handle_recordings.TranslateAdapterImpl')
    def test_get_video_path_returns_none_when_not_exists(self, mock_translate, mock_bili):
        """Test _get_video_path returns None when path doesn't exist."""
        mock_translate.return_value = mock.MagicMock()
        mock_bili.return_value = mock.MagicMock()

        handler = HandleRecording(self.community)
        handler.meeting_adapter_impl.get_video = mock.MagicMock(return_value='/nonexistent/path.mp4')

        result = handler._get_video_path({'mid': 'test_mid'})

        self.assertIsNone(result)


class HandleRecordingGetValidQueryRangeTest(TestCommonMeeting):
    """Test HandleRecording._get_valid_query_range static method."""

    def setUp(self):
        super().setUp()

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @override_settings(BILI_UPLOAD_DATE=7)
    def test_get_valid_query_range_returns_correct_format(self):
        """Test _get_valid_query_range returns correct date format."""
        result = HandleRecording._get_valid_query_range()

        self.assertEqual(len(result), 2)
        start_date, end_date = result

        # Check format: start is YYYY-MM-DD HH:MM, end is YYYY-MM-DD
        self.assertRegex(start_date, r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$')
        self.assertRegex(end_date, r'^\d{4}-\d{2}-\d{2}$')


class HandleRecordingWorkflowTest(TestCommonMeeting):
    """Test handle_recordings work_flow function."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.management.commands.handle_recordings.BiliAdapterImpl')
    @mock.patch('meeting.management.commands.handle_recordings.TranslateAdapterImpl')
    @mock.patch('meeting.management.commands.handle_recordings.HandleRecording.upload_obs')
    @mock.patch('meeting.management.commands.handle_recordings.HandleRecording.upload_bili')
    @override_settings(IS_UPLOAD_OBS=True, IS_UPLOAD_BILI=True)
    def test_workflow_calls_upload_methods(self, mock_upload_bili, mock_upload_obs, mock_translate, mock_bili):
        """Test work_flow calls upload methods when settings enabled."""
        from meeting.management.commands.handle_recordings import work_flow

        mock_translate.return_value = mock.MagicMock()
        mock_bili.return_value = mock.MagicMock()
        mock_upload_obs.return_value = {}
        mock_upload_bili.return_value = None

        handler = HandleRecording(self.community)
        work_flow(handler)

        mock_upload_obs.assert_called_once()
        mock_upload_bili.assert_called_once_with({})

    @mock.patch('meeting.management.commands.handle_recordings.BiliAdapterImpl')
    @mock.patch('meeting.management.commands.handle_recordings.TranslateAdapterImpl')
    @mock.patch('meeting.management.commands.handle_recordings.HandleRecording.upload_obs')
    @override_settings(IS_UPLOAD_OBS=False, IS_UPLOAD_BILI=False)
    def test_workflow_skips_obs_when_disabled(self, mock_upload_obs, mock_translate, mock_bili):
        """Test work_flow skips upload_obs when setting disabled."""
        from meeting.management.commands.handle_recordings import work_flow

        mock_translate.return_value = mock.MagicMock()
        mock_bili.return_value = mock.MagicMock()

        handler = HandleRecording(self.community)
        work_flow(handler)

        mock_upload_obs.assert_not_called()


class HandleRecordingCommandTest(TestCommonMeeting):
    """Test handle_recordings Command class."""

    def setUp(self):
        super().setUp()

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.management.commands.handle_recordings.HandleRecording')
    @override_settings(COMMUNITY_SUPPORT=['openEuler'])
    def test_command_creates_handlers_for_all_communities(self, mock_handler_class):
        """Test Command creates handlers for all supported communities."""
        from meeting.management.commands.handle_recordings import Command

        mock_handler = mock.MagicMock()
        mock_handler_class.return_value = mock_handler

        command = Command()
        command.handle()

        mock_handler_class.assert_called_with('openEuler')


class HandleMeetingStatusCommandTest(TestCommonMeeting):
    """Test handle_meeting_status Command class."""

    def setUp(self):
        super().setUp()

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.management.commands.handle_meeting_status.HandleMeetingStatus')
    @override_settings(COMMUNITY_SUPPORT=['openEuler'])
    def test_command_creates_handlers_for_all_communities(self, mock_handler_class):
        """Test Command creates handlers for all supported communities."""
        from meeting.management.commands.handle_meeting_status import Command

        mock_handler = mock.MagicMock()
        mock_handler_class.return_value = mock_handler

        command = Command()
        command.handle()

        mock_handler_class.assert_called_with('openEuler')


class ScanUploadRecordingStaticMethodTest(TestCommonMeeting):
    """Test scan_upload_meetings.py static methods."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def test_cover_content_formatting(self):
        """Test _cover_content generates correct HTML template."""
        from meeting.management.commands.scan_upload_meetings import ScanUploadRecording

        content = ScanUploadRecording._cover_content(
            topic="Test Topic",
            date="2026-04-15"
        )

        # Verify HTML structure
        self.assertIn("<!DOCTYPE html>", content)
        self.assertIn("Test Topic", content)
        self.assertIn("2026-04-15", content)

    def test_cover_content_static(self):
        """Test _cover_content as static method directly."""
        from meeting.management.commands.scan_upload_meetings import ScanUploadRecording

        content = ScanUploadRecording._cover_content(
            topic="VLLM Meeting",
            date="2026-04-16"
        )

        self.assertIn("VLLM Meeting", content)
        self.assertIn("2026-04-16", content)


class ScanUploadRecordingInitTest(TestCommonMeeting):
    """Test ScanUploadRecording initialization."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def test_init_sets_community(self):
        """Test ScanUploadRecording.__init__ sets community."""
        from meeting.management.commands.scan_upload_meetings import ScanUploadRecording

        handler = ScanUploadRecording(self.community)
        self.assertEqual(handler.community, self.community)

    def test_init_has_class_attributes(self):
        """Test ScanUploadRecording has class attributes."""
        from meeting.management.commands.scan_upload_meetings import ScanUploadRecording

        handler = ScanUploadRecording(self.community)
        self.assertIsNotNone(handler.meeting_adapter_impl)
        self.assertIsNotNone(handler.bili_adapter_impl)
        self.assertIsNotNone(handler.upload_obs_adapter_impl)
        self.assertIsNotNone(handler.upload_bili_adapter_impl)
        self.assertIsNotNone(handler.meeting_cache_dao)


class ScanUploadRecordingScanVideoTest(TestCommonMeeting):
    """Test ScanUploadRecording.scan_video method."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.management.commands.scan_upload_meetings.ZoomApi.meeting_type', 'zoom')
    @mock.patch('meeting.management.commands.scan_upload_meetings.ZoomApi')
    @override_settings(COMMUNITY_HOST={'openEuler': {'ZOOM': [{'HOST': 'test@test.com'}]}})
    def test_scan_video_returns_empty_when_no_new_videos(self, mock_zoom_api):
        """Test scan_video returns empty dict when no new videos."""
        from meeting.management.commands.scan_upload_meetings import ScanUploadRecording

        mock_zoom_instance = mock.MagicMock()
        mock_zoom_instance.get_video_by_day.return_value = []
        mock_zoom_instance.get_video_url_by_records.return_value = {}
        mock_zoom_api.return_value = mock_zoom_instance

        handler = ScanUploadRecording(self.community)
        handler.meeting_cache_dao.get_by_meeting_id = mock.MagicMock(return_value=None)

        result = handler.scan_video()

        self.assertIsInstance(result, dict)

    @mock.patch('meeting.management.commands.scan_upload_meetings.ZoomApi.meeting_type', 'zoom')
    @mock.patch('meeting.management.commands.scan_upload_meetings.ZoomApi')
    @override_settings(COMMUNITY_HOST={'openEuler': {'ZOOM': [{'HOST': 'test@test.com'}]}})
    def test_scan_video_filters_cached_videos(self, mock_zoom_api):
        """Test scan_video filters out already cached videos."""
        from meeting.management.commands.scan_upload_meetings import ScanUploadRecording

        mock_zoom_instance = mock.MagicMock()
        mock_zoom_instance.get_video_by_day.return_value = [
            {'uuid': 'cached_uuid', 'id': 'test_id'},
            {'uuid': 'new_uuid', 'id': 'new_id'}
        ]
        mock_zoom_instance.get_video_url_by_records.return_value = {'path': {'id': 'new_id'}}
        mock_zoom_api.return_value = mock_zoom_instance

        handler = ScanUploadRecording(self.community)
        # Mock: first video is cached, second is new
        def mock_get_by_meeting_id(uuid):
            if uuid == 'cached_uuid':
                return mock.MagicMock()  # Already cached
            return None  # New video
        handler.meeting_cache_dao.get_by_meeting_id = mock.MagicMock(side_effect=mock_get_by_meeting_id)

        result = handler.scan_video()

        # Should call get_video_url_by_records with filtered list (only new_uuid)
        mock_zoom_instance.get_video_url_by_records.assert_called_once()


class ScanUploadRecordingWorkflowTest(TestCommonMeeting):
    """Test scan_upload_meetings work_flow function."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.management.commands.scan_upload_meetings.ScanUploadRecording.scan_video')
    def test_workflow_handles_empty_scan_result(self, mock_scan_video):
        """Test work_flow handles empty scan result."""
        from meeting.management.commands.scan_upload_meetings import ScanUploadRecording, work_flow

        mock_scan_video.return_value = {}

        handler = ScanUploadRecording(self.community)
        work_flow(handler)

        mock_scan_video.assert_called_once()


class SendFailedEmailTest(TestCommonMeeting):
    """Test send_failed_email function."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.management.commands.scan_upload_meetings.EmailAdapter')
    @override_settings(COMMUNITY_SMTP={'openEuler': {'SMTP_MESSAGE_TO': 'admin@test.com'}})
    def test_send_failed_email_creates_message(self, mock_email_adapter):
        """Test send_failed_email creates message correctly."""
        from meeting.management.commands.scan_upload_meetings import send_failed_email

        mock_adapter_instance = mock.MagicMock()
        mock_email_adapter.return_value = mock_adapter_instance

        send_failed_email(self.community, "Test error message")

        mock_email_adapter.assert_called_once_with(self.community)
        mock_adapter_instance.send_message.assert_called_once()


class ScanUploadRecordingCommandTest(TestCommonMeeting):
    """Test scan_upload_meetings Command class."""

    def setUp(self):
        super().setUp()

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.management.commands.scan_upload_meetings.ScanUploadRecording')
    @override_settings(COMMUNITY_SUPPORT=['openEuler'])
    def test_command_creates_handlers_for_all_communities(self, mock_handler_class):
        """Test Command creates handlers for all supported communities."""
        from meeting.management.commands.scan_upload_meetings import Command

        mock_handler = mock.MagicMock()
        mock_handler_class.return_value = mock_handler

        command = Command()
        command.handle()

        mock_handler_class.assert_called_with('openEuler')


class MeetingCacheDaoTest(TestCommonMeeting):
    """Test MeetingCacheDao methods."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def test_meeting_cache_dao_create(self):
        """Test MeetingCacheDao.create creates cache record."""
        from meeting.infrastructure.dao.meeting_cache_dao import MeetingCacheDao

        result = MeetingCacheDao.create(meeting_id="test_uuid", vid="BV123456")

        self.assertIsNotNone(result)
        self.assertEqual(result.meeting_id, "test_uuid")
        self.assertEqual(result.vid, "BV123456")

    def test_meeting_cache_dao_get_by_meeting_id(self):
        """Test MeetingCacheDao.get_by_meeting_id retrieves record."""
        from meeting.infrastructure.dao.meeting_cache_dao import MeetingCacheDao

        # Create a cache record first
        MeetingCacheDao.create(meeting_id="test_uuid_2", vid="BV789")

        result = MeetingCacheDao.get_by_meeting_id("test_uuid_2")

        self.assertIsNotNone(result)
        self.assertEqual(result.meeting_id, "test_uuid_2")


class HandleRecordingUploadBiliAllTest(TestCommonMeeting):
    """Test HandleRecording.upload_bili method."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"
        self.today = datetime.datetime.now().strftime('%Y-%m-%d')

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    @mock.patch('meeting.management.commands.handle_recordings.BiliAdapterImpl')
    @mock.patch('meeting.management.commands.handle_recordings.TranslateAdapterImpl')
    @mock.patch('meeting.management.commands.handle_recordings.HandleRecording._get_video_path')
    @mock.patch('meeting.management.commands.handle_recordings.HandleRecording._get_video_cover_path')
    @mock.patch('meeting.infrastructure.dao.meeting_records_bili_dao.MeetingRecordsBiliDao.update_by_mid')
    def test_upload_bili_empty_cache_path(self, mock_update, mock_cover_path, mock_video_path, mock_translate, mock_bili):
        """Test upload_bili with empty cache path."""
        mock_translate.return_value = mock.MagicMock()
        mock_bili.return_value = mock.MagicMock()

        handler = HandleRecording(self.community)
        # Call upload_bili with empty dict
        handler.upload_bili({})

        # Should complete without errors
        mock_video_path.assert_not_called()


class HandleRecordingCoverContentTest(TestCommonMeeting):
    """Test HandleRecording cover content static method."""

    def setUp(self):
        super().setUp()
        self.community = "openEuler"

    def tearDown(self):
        self.clear_meetings()
        self.clear_all_users()

    def test_cover_content_includes_topic(self):
        """Test _cover_content includes topic in HTML."""
        content = HandleRecording._cover_content("Test Meeting", "test_group", "2026-04-15", "10:00", "11:00")
        self.assertIn("Test Meeting", content)
        self.assertIn("2026-04-15", content)
        self.assertIn("10:00-11:00", content)

    def test_cover_content_html_structure(self):
        """Test _cover_content has correct HTML structure."""
        content = HandleRecording._cover_content("Topic", "Group", "Date", "10:00", "11:00")
        self.assertIn("<!DOCTYPE html>", content)
        self.assertIn("<html", content)
        self.assertIn("</html>", content)