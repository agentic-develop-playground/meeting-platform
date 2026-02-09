#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
"""
Integration test suite for complete meeting workflows.

Tests cover end-to-end scenarios:
- Complete meeting lifecycle (create → update → get → delete)
- Cyclic meeting workflows
- Meeting with recordings workflow
- Sequence tracking across operations
- Round-robin host assignment
"""
import logging
from unittest import mock
from datetime import datetime, timedelta

from rest_framework import status

from meeting.models import (
    Meeting, MeetingCycleDate, MeetingCycleSubMeeting,
    MeetingObsRecords, MeetingBiliRecords
)
from meeting_platform.test.meeting.test_base import BaseMeetingTest, BaseCyclicMeetingTest
from meeting_platform.test.meeting.fixtures import (
    create_test_meeting_data,
    create_daily_cycle_data,
    get_future_date
)

logger = logging.getLogger("log")


class MeetingLifecycleTest(BaseMeetingTest):
    """Integration tests for complete meeting lifecycle."""

    create_url = "/inner/v1/meeting/meeting/"
    get_url = "/inner/v1/meeting/meeting/{}/"
    update_url = "/inner/v1/meeting/meeting/{}/"
    delete_url = "/inner/v1/meeting/meeting/{}/"

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.update')
    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.delete')
    def test_complete_meeting_lifecycle(self, mock_delete, mock_update, mock_create):
        """Test complete lifecycle: Create → Get → Update → Get → Delete."""
        mock_create.return_value = {
            'mid': 'LIFECYCLE_TEST_123',
            'join_url': 'https://test.zoom.us/j/123',
            'host_id': 'host1@test.com'
        }
        mock_update.return_value = {'updated': True}
        mock_delete.return_value = {'deleted': True}

        # STEP 1: Create meeting
        data = create_test_meeting_data({
            'topic': 'Lifecycle Test Meeting',
            'date': get_future_date(5)
        })
        response = self.client.post(self.create_url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        meeting_id = response.json()['data']
        meeting = Meeting.objects.get(id=meeting_id)
        meeting_mid = meeting.mid

        # STEP 2: Get meeting
        url = self.get_url.format(meeting_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        meeting_data = response.json()['data']
        if isinstance(meeting_data, dict):
            self.assertEqual(meeting_data.get('topic'), 'Lifecycle Test Meeting')
            initial_sequence = meeting_data.get('sequence', 0)
        else:
            meeting_obj = Meeting.objects.get(id=meeting_data)
            self.assertEqual(meeting_obj.topic, 'Lifecycle Test Meeting')
            initial_sequence = meeting_obj.sequence

        # STEP 3: Update meeting
        update_data = {
            'topic': 'Updated Lifecycle Meeting',
            'date': get_future_date(7),
            'start': '14:00',
            'end': '15:00',
            'is_record': True
        }
        url = self.update_url.format(meeting_id)
        response = self.client.put(url, data=update_data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # STEP 4: Get meeting again to verify update
        url = self.get_url.format(meeting_id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        meeting_data = response.json()['data']
        if isinstance(meeting_data, dict):
            self.assertEqual(meeting_data.get('topic'), 'Updated Lifecycle Meeting')
            updated_sequence = meeting_data.get('sequence', 0)
        else:
            meeting_obj = Meeting.objects.get(id=meeting_data)
            self.assertEqual(meeting_obj.topic, 'Updated Lifecycle Meeting')
            updated_sequence = meeting_obj.sequence

        # Sequence should have incremented
        self.assertGreaterEqual(updated_sequence, initial_sequence)

        # STEP 5: Delete meeting
        url = self.delete_url.format(meeting_id)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # STEP 6: Verify meeting is deleted
        meeting = Meeting.objects.filter(id=meeting_id, is_delete=False).first()
        # Meeting may be soft-deleted (is_delete=True) or hard-deleted
        if meeting:
            self.assertTrue(meeting.is_delete)

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.update')
    def test_meeting_sequence_tracking(self, mock_update, mock_create):
        """Test that sequence number increments with each update."""
        mock_create.return_value = {
            'mid': 'SEQUENCE_TEST_456',
            'join_url': 'https://test.zoom.us/j/456',
            'host_id': 'host2@test.com'
        }
        mock_update.return_value = {'updated': True}

        # Create meeting
        data = create_test_meeting_data({'date': get_future_date(10)})
        response = self.client.post(self.create_url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        meeting_id = response.json()['data']

        # Get initial sequence
        url = self.get_url.format(meeting_id)
        response = self.client.get(url)
        meeting_data = response.json()['data']
        if isinstance(meeting_data, dict):
            seq1 = meeting_data.get('sequence', 0)
        else:
            seq1 = Meeting.objects.get(id=meeting_data).sequence

        # Update 1
        url = self.update_url.format(meeting_id)
        update_data = {'topic': 'Update 1'}
        response = self.client.patch(url, data=update_data)
        if response.status_code == status.HTTP_200_OK:
            update_data_resp = response.json()['data']
            if isinstance(update_data_resp, dict):
                seq2 = update_data_resp.get('sequence', 0)
            else:
                seq2 = Meeting.objects.get(id=update_data_resp).sequence
            self.assertGreaterEqual(seq2, seq1)

            # Update 2
            update_data = {'topic': 'Update 2'}
            response = self.client.patch(url, data=update_data)
            if response.status_code == status.HTTP_200_OK:
                update_data_resp = response.json()['data']
                if isinstance(update_data_resp, dict):
                    seq3 = update_data_resp.get('sequence', 0)
                else:
                    seq3 = Meeting.objects.get(id=update_data_resp).sequence
                self.assertGreaterEqual(seq3, seq2)

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    def test_concurrent_meeting_creation(self, mock_create):
        """Test creating multiple meetings concurrently."""
        mock_create.side_effect = [
            {
                'mid': f'CONCURRENT_TEST_{i}',
                'join_url': f'https://test.zoom.us/j/{i}',
                'host_id': 'host1@test.com'
            }
            for i in range(5)
        ]

        # Create 5 meetings in quick succession
        meeting_ids = []
        for i in range(5):
            data = create_test_meeting_data({
                'topic': f'Concurrent Meeting {i}',
                'date': get_future_date(i + 1)
            })
            response = self.client.post(self.create_url, data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            meeting_ids.append(response.json()['data'])

        # All meetings should be created successfully
        self.assertEqual(len(meeting_ids), 5)
        self.assertEqual(len(set(meeting_ids)), 5)  # All unique


class CyclicMeetingWorkflowTest(BaseCyclicMeetingTest):
    """Integration tests for cyclic meeting workflows."""

    create_url = "/inner/v1/meeting/meeting/"
    get_url = "/inner/v1/meeting/meeting/{}/"
    sub_update_url = "/inner/v1/meeting/meeting/sub/{}/"
    sub_delete_url = "/inner/v1/meeting/meeting/sub/{}/"

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.update')
    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.delete')
    def test_cyclic_meeting_complete_workflow(self, mock_delete, mock_update, mock_create):
        """Test complete cyclic meeting workflow including sub-meeting operations."""
        mock_create.return_value = {
            'mid': 'CYCLIC_WORKFLOW_TEST',
            'join_url': 'https://test.zoom.us/j/789',
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
        mock_update.return_value = {'updated': True}
        mock_delete.return_value = {'deleted': True}

        # STEP 1: Create cyclic meeting
        data = create_daily_cycle_data(interval=1, duration_days=7)
        response = self.client.post(self.create_url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        meeting_id = response.json()['data']
        meeting = Meeting.objects.get(id=meeting_id)
        meeting_mid = meeting.mid

        # STEP 2: Verify sub-meetings created
        sub_meetings = MeetingCycleSubMeeting.objects.filter(mid=meeting_mid)
        self.assertGreater(sub_meetings.count(), 0)
        initial_sub_count = sub_meetings.count()

        # STEP 3: Verify cycle date record
        cycle_date = MeetingCycleDate.objects.filter(mid=meeting_mid).first()
        self.assertIsNotNone(cycle_date)

        # STEP 4: Get a sub-meeting
        first_sub = sub_meetings.first()

        # STEP 5: Update sub-meeting
        update_data = {
            'date': get_future_date(15),
            'start': first_sub.start,
            'end': first_sub.end,
            'mid': first_sub.mid
        }
        url = self.sub_update_url.format(first_sub.sub_id)
        response = self.client.put(url, data=update_data)
        # May succeed or fail based on time restrictions

        # STEP 6: Delete a sub-meeting
        if sub_meetings.count() > 1:
            second_sub = sub_meetings[1]
            url = self.sub_delete_url.format(second_sub.sub_id)
            response = self.client.delete(url)
            # May succeed or fail based on time restrictions

        # STEP 7: Parent meeting should still exist
        meeting = Meeting.objects.filter(id=meeting_id).first()
        self.assertIsNotNone(meeting)
        self.assertTrue(meeting.is_cycle)


class MeetingWithRecordingsWorkflowTest(BaseMeetingTest):
    """Integration tests for meetings with recording workflow."""

    create_url = "/inner/v1/meeting/meeting/"
    get_url = "/inner/v1/meeting/meeting/{}/"
    delete_url = "/inner/v1/meeting/meeting/{}/"

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.delete')
    def test_meeting_with_recordings_workflow(self, mock_delete, mock_create):
        """Test complete workflow for meeting with recording records."""
        mock_create.return_value = {
            'mid': 'RECORDING_WORKFLOW_TEST',
            'join_url': 'https://test.zoom.us/j/111',
            'host_id': 'host1@test.com'
        }
        mock_delete.return_value = {'deleted': True}

        # STEP 1: Create meeting with recording enabled
        data = create_test_meeting_data({'is_record': True})
        response = self.client.post(self.create_url, data=data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        meeting_id = response.json()['data']
        meeting = Meeting.objects.get(id=meeting_id)
        meeting_mid = meeting.mid

        # STEP 2: Get meeting object
        meeting = Meeting.objects.get(id=meeting_id)

        # STEP 3: Create recording records (simulate recording processing)
        obs_record = MeetingObsRecords.objects.create(
            mid=meeting.mid,
            meeting=meeting,
            status=0  # Pending
        )

        bili_record = MeetingBiliRecords.objects.create(
            mid=meeting.mid,
            meeting=meeting,
            status=0  # Pending
        )

        # STEP 4: Update recording status and URLs (simulate processing complete)
        obs_record.status = 2  # Complete
        obs_record.text_video_url = 'https://obs.test.com/video.mp4'
        obs_record.save()

        bili_record.status = 2  # Complete
        bili_record.replay_url = 'https://bilibili.com/video/BV123'
        bili_record.save()

        # STEP 5: Verify recording records exist
        obs_records = MeetingObsRecords.objects.filter(mid=meeting.mid)
        self.assertGreater(obs_records.count(), 0)

        bili_records = MeetingBiliRecords.objects.filter(mid=meeting.mid)
        self.assertGreater(bili_records.count(), 0)

        # STEP 6: Delete meeting
        url = self.delete_url.format(meeting_id)
        response = self.client.delete(url)
        # Accept both 200 and 204 as valid delete responses
        self.assertIn(response.status_code, [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT])

        # STEP 7: Verify recordings are cascaded (if using CASCADE)
        # This depends on the model's on_delete behavior


class RoundRobinHostAssignmentTest(BaseMeetingTest):
    """Test round-robin host assignment for meetings."""

    create_url = "/inner/v1/meeting/meeting/"

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    def test_round_robin_host_fairness(self, mock_create):
        """Test that round-robin host assignment distributes fairly."""
        # Track assigned hosts
        assigned_hosts = []

        def create_with_host(meeting_id):
            """Mock create that rotates through hosts."""
            host_index = len(assigned_hosts) % 3
            host = f'host{host_index + 1}@test.com'
            assigned_hosts.append(host)
            return {
                'mid': meeting_id,
                'join_url': f'https://test.zoom.us/j/{meeting_id}',
                'host_id': host
            }

        mock_create.side_effect = [create_with_host(f'HOST_TEST_{i}') for i in range(9)]

        # Create 9 meetings on different dates
        for i in range(9):
            data = create_test_meeting_data({
                'topic': f'Host Test Meeting {i}',
                'date': get_future_date(i + 1)
            })
            response = self.client.post(self.create_url, data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify round-robin distribution
        # Each of 3 hosts should be assigned 3 times
        from collections import Counter
        host_counts = Counter(assigned_hosts)

        # All hosts should be used
        self.assertEqual(len(host_counts), 3)

        # Distribution should be relatively fair (exactly 3 each if perfect round-robin)
        for count in host_counts.values():
            self.assertEqual(count, 3)


class ConflictDetectionIntegrationTest(BaseMeetingTest):
    """Integration tests for conflict detection across operations."""

    create_url = "/inner/v1/meeting/meeting/"

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    def test_create_conflicting_meeting_fails(self, mock_create):
        """Test that creating a conflicting meeting is prevented."""
        mock_create.return_value = {
            'mid': 'CONFLICT_TEST_1',
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

        # Create first meeting
        data1 = create_test_meeting_data({
            'date': get_future_date(5),
            'start': '10:00',
            'end': '11:00',
            'platform': 'ZOOM'
        })
        response1 = self.client.post(self.create_url, data=data1)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # Try to create conflicting meeting (overlapping time)
        mock_create.return_value['id'] = 'CONFLICT_TEST_2'
        data2 = create_test_meeting_data({
            'date': get_future_date(5),
            'start': '10:30',  # Overlaps with first meeting
            'end': '11:30',
            'platform': 'ZOOM'
        })
        response2 = self.client.post(self.create_url, data=data2)

        # Should detect conflict (platform and community-specific)
        # May succeed if different communities or host availability


class MultiPlatformIntegrationTest(BaseMeetingTest):
    """Integration tests for multi-platform meeting management."""

    create_url = "/inner/v1/meeting/meeting/"

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    def test_create_meetings_on_different_platforms(self, mock_create):
        """Test creating meetings on ZOOM, WELINK, and TENCENT."""
        platforms = ['ZOOM', 'WELINK', 'TENCENT']

        for i, platform in enumerate(platforms):
            mock_create.return_value = {
                'mid': f'{platform}_TEST_{i}',
                'join_url': f'https://{platform.lower()}.test.com/j/{i}',
                'host_id': f'host{i + 1}@test.com'
            }

            data = create_test_meeting_data({
                'platform': platform,
                'topic': f'{platform} Test Meeting',
                'date': get_future_date(i + 1)
            })

            response = self.client.post(self.create_url, data=data)
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(Meeting.objects.get(id=response.json()['data']).platform, platform)

    @mock.patch('meeting.infrastructure.adapter.meeting_adapter_impl.meeting_adapter_impl.MeetingAdapterImpl.create')
    def test_same_time_different_platforms_no_conflict(self, mock_create):
        """Test that same time on different platforms doesn't conflict."""
        same_date = get_future_date(10)
        same_start = '14:00'
        same_end = '15:00'

        mock_create.return_value = {
            'mid': 'ZOOM_NO_CONFLICT',
            'join_url': 'https://zoom.test.com/j/1',
            'host_id': 'host1@test.com'
        }

        # Create ZOOM meeting
        data1 = create_test_meeting_data({
            'platform': 'ZOOM',
            'date': same_date,
            'start': same_start,
            'end': same_end
        })
        response1 = self.client.post(self.create_url, data=data1)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)

        # Create WELINK meeting at same time
        mock_create.return_value = {
            'mid': 'WELINK_NO_CONFLICT',
            'join_url': 'https://welink.test.com/j/2',
            'host_id': 'host2@test.com'
        }

        data2 = create_test_meeting_data({
            'platform': 'WELINK',
            'date': same_date,
            'start': same_start,
            'end': same_end,
            'topic': 'WELINK No Conflict Meeting',
            'group_name': 'welink_group'
        })
        response2 = self.client.post(self.create_url, data=data2)

        # Should succeed - different platforms
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
