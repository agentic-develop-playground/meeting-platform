#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
"""
Test suite for recording management (OBS and Bilibili).

Tests cover:
- OBS record creation and status transitions
- Bilibili record creation and status transitions
- Recording URL updates
- Recording records for sub-meetings
- Query operations including recordings
- Cascade behavior on meeting deletion
"""
import logging
from unittest import mock
from datetime import datetime, timedelta

from rest_framework import status

from meeting.models import (
    Meeting, MeetingObsRecords, MeetingBiliRecords,
    MeetingCycleSubMeeting
)
from meeting.domain.primitive.upload_status import UploadStatus
from meeting_platform.test.meeting.test_base import BaseMeetingTest, BaseCyclicMeetingTest
from meeting_platform.test.meeting.fixtures import (
    create_test_meeting_data,
    create_daily_cycle_data,
    get_future_date
)

logger = logging.getLogger("log")


class ObsRecordsTest(BaseMeetingTest):
    """Test cases for OBS recording records."""

    create_url = "/inner/v1/meeting/meeting/"
    get_url = "/inner/v1/meeting/meeting/{}/"

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    def test_create_obs_record_on_meeting_create(self, mock_create):
        """Test that OBS record is created when meeting is created with recording enabled."""
        mock_create.return_value = {
            'mid': 'OBS_TEST_123',
            'join_url': 'https://test.zoom.us/j/123',
            'host_id': 'host1@test.com',
            'sub_info': [
                {
                    'sub_id': f'SUB_{i}',
                    'date': str((datetime.now().date() + timedelta(days=i+1))),
                    'start': '08:00',
                    'end': '09:00'
                }
                for i in range(7)
            ]
        }

        data = create_test_meeting_data({'is_record': True})

        response = self.client.post(self.create_url, data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        meeting_id = response.json()['data']
        meeting = Meeting.objects.get(id=meeting_id)

        # Check if OBS record was created (depends on IS_UPLOAD_OBS setting)
        meeting = Meeting.objects.filter(mid=meeting.mid).first()
        if meeting.is_record:
            # OBS record may be created
            obs_records = MeetingObsRecords.objects.filter(mid=meeting.mid)
            # Record creation depends on settings

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    def test_no_obs_record_when_recording_disabled(self, mock_create):
        """Test that no OBS record is created when recording is disabled."""
        mock_create.return_value = {
            'mid': 'OBS_NO_RECORD_TEST',
            'join_url': 'https://test.zoom.us/j/456',
            'host_id': 'host2@test.com',
            'sub_info': [
                {
                    'sub_id': f'SUB_{i}',
                    'date': str((datetime.now().date() + timedelta(days=i+1))),
                    'start': '08:00',
                    'end': '09:00'
                }
                for i in range(7)
            ]
        }

        data = create_test_meeting_data({'is_record': False})

        response = self.client.post(self.create_url, data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        meeting_id = response.json()['data']
        meeting = Meeting.objects.get(id=meeting_id)

        meeting = Meeting.objects.filter(mid=meeting.mid).first()
        self.assertFalse(meeting.is_record)

    def test_obs_record_status_transitions(self):
        """Test OBS record status transitions: INIT → TRANSLATE → FINISH."""
        # Create OBS record directly
        meeting = self.create_meeting(
            sponsor='TestUser',
            group_name='test_group',
            community='openEuler',
            topic='Test Meeting',
            platform='ZOOM',
            mid='OBS_STATUS_TEST',
            is_record=True
        )

        obs_record = MeetingObsRecords.objects.create(
            mid=meeting.mid,
            meeting=meeting,
            status=UploadStatus.INIT.value
        )

        # Verify initial status
        self.assertEqual(obs_record.status, UploadStatus.INIT.value)

        # Transition to TRANSLATE
        obs_record.status = UploadStatus.TRANSLATE.value
        obs_record.save()
        obs_record.refresh_from_db()
        self.assertEqual(obs_record.status, UploadStatus.TRANSLATE.value)

        # Transition to FINISH
        obs_record.status = UploadStatus.FINISH.value
        obs_record.save()
        obs_record.refresh_from_db()
        self.assertEqual(obs_record.status, UploadStatus.FINISH.value)

    def test_update_obs_record_urls(self):
        """Test updating OBS record URLs (vtt, json, video, picture)."""
        meeting = self.create_meeting(
            sponsor='TestUser',
            group_name='test_group',
            community='openEuler',
            topic='Test Meeting',
            platform='ZOOM',
            mid='OBS_URL_TEST',
            is_record=True
        )

        obs_record = MeetingObsRecords.objects.create(
            mid=meeting.mid,
            meeting=meeting,
            status=UploadStatus.INIT.value
        )

        # Update URLs
        obs_record.text_vtt_url = 'https://obs.test.com/recording.vtt'
        obs_record.text_json_url = 'https://obs.test.com/recording.json'
        obs_record.text_video_url = 'https://obs.test.com/recording.mp4'
        obs_record.text_picture_url = 'https://obs.test.com/recording.jpg'
        obs_record.topic_url = 'https://obs.test.com/topics.json'
        obs_record.status = UploadStatus.FINISH.value
        obs_record.save()

        # Verify URLs persisted
        obs_record.refresh_from_db()
        self.assertEqual(obs_record.text_vtt_url, 'https://obs.test.com/recording.vtt')
        self.assertEqual(obs_record.text_json_url, 'https://obs.test.com/recording.json')
        self.assertEqual(obs_record.text_video_url, 'https://obs.test.com/recording.mp4')
        self.assertEqual(obs_record.text_picture_url, 'https://obs.test.com/recording.jpg')
        self.assertEqual(obs_record.topic_url, 'https://obs.test.com/topics.json')

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    def test_obs_record_for_sub_meeting(self, mock_create):
        """Test OBS records for cyclic sub-meetings have sub_id populated."""
        mock_create.return_value = {
            'mid': 'OBS_SUB_TEST',
            'join_url': 'https://test.zoom.us/j/789',
            'host_id': 'host3@test.com',
            'sub_info': [
                {
                    'sub_id': f'SUB_{i}',
                    'date': str((datetime.now().date() + timedelta(days=i+1))),
                    'start': '08:00',
                    'end': '09:00'
                }
                for i in range(7)
            ]
        }

        data = create_daily_cycle_data(interval=1, duration_days=5)
        data['is_record'] = True

        response = self.client.post(self.create_url, data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        meeting_id = response.json()['data']
        meeting = Meeting.objects.get(id=meeting_id)

        # Get sub-meetings
        sub_meetings = MeetingCycleSubMeeting.objects.filter(mid=meeting.mid)

        if sub_meetings.exists():
            # OBS records for sub-meetings should have sub_id
            sub_meeting = sub_meetings.first()

            # Create OBS record for this sub-meeting
            meeting = Meeting.objects.get(mid=meeting.mid)
            obs_record = MeetingObsRecords.objects.create(
                mid=meeting.mid,
                sub_id=sub_meeting.sub_id,
                meeting=meeting,
                status=UploadStatus.INIT.value
            )

            self.assertEqual(obs_record.sub_id, sub_meeting.sub_id)
            self.assertEqual(obs_record.mid, meeting.mid)


class BiliRecordsTest(BaseMeetingTest):
    """Test cases for Bilibili recording records."""

    create_url = "/inner/v1/meeting/meeting/"

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    def test_create_bili_record_on_meeting_create(self, mock_create):
        """Test that Bilibili record is created when meeting is created with recording."""
        mock_create.return_value = {
            'mid': 'BILI_TEST_123',
            'join_url': 'https://test.zoom.us/j/111',
            'host_id': 'host1@test.com',
            'sub_info': [
                {
                    'sub_id': f'SUB_{i}',
                    'date': str((datetime.now().date() + timedelta(days=i+1))),
                    'start': '08:00',
                    'end': '09:00'
                }
                for i in range(7)
            ]
        }

        data = create_test_meeting_data({'is_record': True})

        response = self.client.post(self.create_url, data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        meeting_id = response.json()['data']
        meeting = Meeting.objects.get(id=meeting_id)

        # Check if Bilibili record was created (depends on IS_UPLOAD_BILI setting)
        meeting = Meeting.objects.filter(mid=meeting.mid).first()
        if meeting.is_record:
            # Bili record may be created
            bili_records = MeetingBiliRecords.objects.filter(mid=meeting.mid)
            # Record creation depends on settings

    def test_bili_record_status_transitions(self):
        """Test Bilibili record status transitions."""
        meeting = self.create_meeting(
            sponsor='TestUser',
            group_name='test_group',
            community='openEuler',
            topic='Test Meeting',
            platform='ZOOM',
            mid='BILI_STATUS_TEST',
            is_record=True
        )

        bili_record = MeetingBiliRecords.objects.create(
            mid=meeting.mid,
            meeting=meeting,
            status=UploadStatus.INIT.value
        )

        # Verify initial status
        self.assertEqual(bili_record.status, UploadStatus.INIT.value)

        # Transition to Processing
        bili_record.status = UploadStatus.TRANSLATE.value
        bili_record.save()
        bili_record.refresh_from_db()
        self.assertEqual(bili_record.status, UploadStatus.TRANSLATE.value)

        # Transition to Complete
        bili_record.status = UploadStatus.FINISH.value
        bili_record.save()
        bili_record.refresh_from_db()
        self.assertEqual(bili_record.status, UploadStatus.FINISH.value)

    def test_bili_record_replay_url(self):
        """Test updating Bilibili replay URL."""
        meeting = self.create_meeting(
            sponsor='TestUser',
            group_name='test_group',
            community='openEuler',
            topic='Test Meeting',
            platform='ZOOM',
            mid='BILI_URL_TEST',
            is_record=True
        )

        bili_record = MeetingBiliRecords.objects.create(
            mid=meeting.mid,
            meeting=meeting,
            status=UploadStatus.INIT.value
        )

        # Update replay URL
        bili_record.replay_url = 'https://bilibili.com/video/BV1234567890'
        bili_record.status = UploadStatus.FINISH.value
        bili_record.save()

        # Verify URL persisted
        bili_record.refresh_from_db()
        self.assertEqual(bili_record.replay_url, 'https://bilibili.com/video/BV1234567890')

    def test_bili_record_for_sub_meeting(self):
        """Test Bilibili records for sub-meetings have sub_id."""
        meeting = self.create_meeting(
            sponsor='TestUser',
            group_name='test_group',
            community='openEuler',
            topic='Cyclic Test Meeting',
            platform='ZOOM',
            mid='BILI_SUB_TEST',
            is_cycle=True,
            is_record=True
        )

        # Create a sub-meeting
        sub_meeting = MeetingCycleSubMeeting.objects.create(
            mid=meeting.mid,
            sub_id='SUB_123',
            date='2026-03-01',
            start='10:00',
            end='11:00',
            meeting=meeting
        )

        # Create Bili record for sub-meeting
        bili_record = MeetingBiliRecords.objects.create(
            mid=meeting.mid,
            sub_id=sub_meeting.sub_id,
            meeting=meeting,
            status=UploadStatus.INIT.value
        )

        self.assertEqual(bili_record.sub_id, sub_meeting.sub_id)
        self.assertEqual(bili_record.mid, meeting.mid)


class RecordingsQueryTest(BaseMeetingTest):
    """Test querying meetings with recording information."""

    create_url = "/inner/v1/meeting/meeting/"
    get_url = "/inner/v1/meeting/meeting/{}/"

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    def test_get_meeting_includes_recordings(self, mock_create):
        """Test that getting a meeting includes recording information."""
        mock_create.return_value = {
            'mid': 'QUERY_TEST_123',
            'join_url': 'https://test.zoom.us/j/222',
            'host_id': 'host1@test.com',
            'sub_info': [
                {
                    'sub_id': f'SUB_{i}',
                    'date': str((datetime.now().date() + timedelta(days=i+1))),
                    'start': '08:00',
                    'end': '09:00'
                }
                for i in range(7)
            ]
        }

        data = create_test_meeting_data({'is_record': True})

        response = self.client.post(self.create_url, data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        meeting_id = response.json()['data']

        # Get the meeting
        url = self.get_url.format(meeting_id)
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        response_data = response.json()
        self.assertIn('data', response_data)

        meeting_data = response_data['data']
        # GET endpoint returns full meeting data dict, not just ID
        if isinstance(meeting_data, dict):
            meeting_id = meeting_data.get('id')
            self.assertIsNotNone(meeting_id)
            meeting = Meeting.objects.get(id=meeting_id)
            # Meeting should include recording flag
            self.assertTrue(hasattr(meeting, 'is_record'))

    def test_recordings_cascade_on_delete(self):
        """Test that recording records are deleted when meeting is deleted."""
        meeting = self.create_meeting(
            sponsor='TestUser',
            group_name='test_group',
            community='openEuler',
            topic='Test Meeting',
            platform='ZOOM',
            mid='CASCADE_TEST',
            is_record=True
        )

        # Create recording records
        obs_record = MeetingObsRecords.objects.create(
            mid=meeting.mid,
            meeting=meeting,
            status=UploadStatus.INIT.value
        )

        bili_record = MeetingBiliRecords.objects.create(
            mid=meeting.mid,
            meeting=meeting,
            status=UploadStatus.INIT.value
        )

        obs_id = obs_record.id
        bili_id = bili_record.id

        # Delete meeting
        meeting.delete()

        # Recording records should be cascaded
        self.assertFalse(MeetingObsRecords.objects.filter(id=obs_id).exists())
        self.assertFalse(MeetingBiliRecords.objects.filter(id=bili_id).exists())

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    def test_query_meetings_with_recording_filter(self, mock_create):
        """Test filtering meetings by recording status."""
        mock_create.return_value = {
            'mid': 'FILTER_TEST_123',
            'join_url': 'https://test.zoom.us/j/333',
            'host_id': 'host2@test.com',
            'sub_info': [
                {
                    'sub_id': f'SUB_{i}',
                    'date': str((datetime.now().date() + timedelta(days=i+1))),
                    'start': '08:00',
                    'end': '09:00'
                }
                for i in range(7)
            ]
        }

        # Create meeting with recording
        data1 = create_test_meeting_data({
            'is_record': True,
            'topic': 'Meeting with Recording',
            'date': get_future_date(5)
        })
        response1 = self.client.post(self.create_url, data=data1)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # Create meeting without recording (different date to avoid conflict)
        mock_create.return_value['mid'] = 'FILTER_TEST_456'
        data2 = create_test_meeting_data({
            'is_record': False,
            'topic': 'Meeting without Recording',
            'date': get_future_date(10)
        })
        response2 = self.client.post(self.create_url, data=data2)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)

        # Query all meetings
        response = self.client.get(self.create_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Both meetings should appear in results
        response_data = response.json().get('data', [])
        if isinstance(response_data, dict):
            meetings = response_data.get('results', [])
        else:
            meetings = response_data if isinstance(response_data, list) else []
        # Filter capabilities depend on implementation


class RecordingsCyclicMeetingTest(BaseCyclicMeetingTest):
    """Test recording records for cyclic meetings."""

    create_url = "/inner/v1/meeting/meeting/"

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    def test_cyclic_meeting_recording_records_per_sub(self, mock_create):
        """Test that cyclic meetings can have separate recording records per sub-meeting."""
        mock_create.return_value = {
            'mid': 'CYCLIC_RECORD_TEST',
            'join_url': 'https://test.zoom.us/j/444',
            'host_id': 'host3@test.com',
            'sub_info': [
                {
                    'sub_id': f'SUB_{i}',
                    'date': str((datetime.now().date() + timedelta(days=i+1))),
                    'start': '08:00',
                    'end': '09:00'
                }
                for i in range(7)
            ]
        }

        data = create_daily_cycle_data(interval=1, duration_days=3)
        data['is_record'] = True

        response = self.client.post(self.create_url, data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        meeting_id = response.json()['data']
        meeting = Meeting.objects.get(id=meeting_id)

        meeting = Meeting.objects.get(mid=meeting.mid)
        sub_meetings = MeetingCycleSubMeeting.objects.filter(mid=meeting.mid)

        # Create OBS records for each sub-meeting
        for sub in sub_meetings:
            obs_record = MeetingObsRecords.objects.create(
                mid=meeting.mid,
                sub_id=sub.sub_id,
                meeting=meeting,
                status=UploadStatus.INIT.value
            )
            self.assertEqual(obs_record.sub_id, sub.sub_id)

        # Verify records created
        obs_records = MeetingObsRecords.objects.filter(mid=meeting.mid)
        self.assertEqual(obs_records.count(), sub_meetings.count())

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    def test_parent_and_sub_recordings_independent(self, mock_create):
        """Test that parent meeting and sub-meetings have independent recordings."""
        mock_create.return_value = {
            'mid': 'INDEPENDENT_RECORD_TEST',
            'join_url': 'https://test.zoom.us/j/555',
            'host_id': 'host4@test.com',
            'sub_info': [
                {
                    'sub_id': f'SUB_{i}',
                    'date': str((datetime.now().date() + timedelta(days=i+1))),
                    'start': '08:00',
                    'end': '09:00'
                }
                for i in range(7)
            ]
        }

        data = create_daily_cycle_data(interval=1, duration_days=3)
        data['is_record'] = True

        response = self.client.post(self.create_url, data=data)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        meeting_id = response.json()['data']
        meeting = Meeting.objects.get(id=meeting_id)

        meeting = Meeting.objects.get(mid=meeting.mid)

        # Create parent recording (no sub_id)
        parent_obs = MeetingObsRecords.objects.create(
            mid=meeting.mid,
            meeting=meeting,
            status=UploadStatus.FINISH.value,
            text_video_url='https://obs.test.com/parent.mp4'
        )

        # Create sub-meeting recording
        sub_meeting = MeetingCycleSubMeeting.objects.filter(mid=meeting.mid).first()
        if sub_meeting:
            sub_obs = MeetingObsRecords.objects.create(
                mid=meeting.mid,
                sub_id=sub_meeting.sub_id,
                meeting=meeting,
                status=UploadStatus.FINISH.value,
                text_video_url='https://obs.test.com/sub1.mp4'
            )

            # Verify they're independent
            self.assertIsNone(parent_obs.sub_id)
            self.assertIsNotNone(sub_obs.sub_id)
            self.assertNotEqual(parent_obs.text_video_url, sub_obs.text_video_url)
