#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
"""
Test utilities including mock classes and assertion helpers.

This module provides mock objects for external services (Email, Kafka, Platform APIs)
and utility functions for common test assertions.
"""
from unittest.mock import Mock, MagicMock
from typing import Dict, Any, List, Optional
import datetime


class MockEmailClient:
    """
    Mock Email client for testing notification functionality.

    Usage:
        with mock.patch('path.to.EmailClient', return_value=MockEmailClient()) as mock_email:
            # Your test code
            mock_email.send_message.assert_called_once()
    """

    def __init__(self):
        self.sent_messages = []
        self.send_message = Mock(side_effect=self._capture_send)
        self.close = Mock()

    def _capture_send(self, **kwargs):
        """Capture sent message details."""
        self.sent_messages.append(kwargs)
        return True

    def get_sent_messages(self) -> List[Dict[str, Any]]:
        """Get all sent messages."""
        return self.sent_messages

    def get_last_message(self) -> Optional[Dict[str, Any]]:
        """Get the last sent message."""
        return self.sent_messages[-1] if self.sent_messages else None

    def assert_message_sent_to(self, recipient: str):
        """Assert a message was sent to specific recipient."""
        for msg in self.sent_messages:
            if recipient in msg.get('to_addr', []):
                return True
        raise AssertionError(f"No message sent to {recipient}")

    def assert_message_contains(self, content: str):
        """Assert any message contains specific content."""
        for msg in self.sent_messages:
            if content in str(msg):
                return True
        raise AssertionError(f"No message contains '{content}'")


class MockKafkaClient:
    """
    Mock Kafka client for testing message queue functionality.

    Usage:
        with mock.patch('path.to.KafKaClient', return_value=MockKafkaClient()) as mock_kafka:
            # Your test code
            mock_kafka.send_msg.assert_called()
    """

    def __init__(self):
        self.sent_messages = []
        self.send_msg = Mock(side_effect=self._capture_message)
        self.close = Mock()

    def _capture_message(self, topic: str, message: Dict[str, Any], **kwargs):
        """Capture sent Kafka message."""
        self.sent_messages.append({
            'topic': topic,
            'message': message,
            'kwargs': kwargs
        })
        return True

    def get_sent_messages(self) -> List[Dict[str, Any]]:
        """Get all sent messages."""
        return self.sent_messages

    def get_messages_by_topic(self, topic: str) -> List[Dict[str, Any]]:
        """Get messages sent to specific topic."""
        return [msg for msg in self.sent_messages if msg['topic'] == topic]

    def assert_message_sent(self, topic: str, expected_payload: Optional[Dict[str, Any]] = None):
        """
        Assert a message was sent to specific topic.

        Args:
            topic: Kafka topic name
            expected_payload: Optional expected message payload
        """
        messages = self.get_messages_by_topic(topic)
        if not messages:
            raise AssertionError(f"No messages sent to topic '{topic}'")

        if expected_payload:
            for msg in messages:
                if msg['message'] == expected_payload:
                    return True
            raise AssertionError(f"No message with expected payload found in topic '{topic}'")

        return True


class MockZoomAPI:
    """
    Mock Zoom API adapter for testing platform-specific functionality.

    Usage:
        with mock.patch('path.to.MeetingAdapterImpl.create') as mock_zoom:
            mock_zoom.return_value = MockZoomAPI.create_success_response()
    """

    @staticmethod
    def create_success_response(meeting_id: str = "123456789") -> Dict[str, Any]:
        """Generate successful Zoom meeting creation response."""
        return {
            'id': meeting_id,
            'join_url': f'https://zoom.us/j/{meeting_id}',
            'host_id': 'test_host@test.com',
            'status': 'waiting'
        }

    @staticmethod
    def update_success_response(meeting_id: str = "123456789") -> Dict[str, Any]:
        """Generate successful Zoom meeting update response."""
        return {
            'id': meeting_id,
            'updated': True
        }

    @staticmethod
    def delete_success_response() -> Dict[str, Any]:
        """Generate successful Zoom meeting deletion response."""
        return {
            'deleted': True
        }

    @staticmethod
    def create_mock_adapter():
        """Create a mock adapter with all CRUD methods."""
        adapter = Mock()
        adapter.create = Mock(return_value=MockZoomAPI.create_success_response())
        adapter.update = Mock(return_value=MockZoomAPI.update_success_response())
        adapter.delete = Mock(return_value=MockZoomAPI.delete_success_response())
        return adapter


class MockWeLinkAPI:
    """
    Mock WeLink API adapter for testing.

    Similar to MockZoomAPI but for WeLink-specific responses.
    """

    @staticmethod
    def create_success_response(meeting_id: str = "WL123456") -> Dict[str, Any]:
        """Generate successful WeLink meeting creation response."""
        return {
            'conferenceID': meeting_id,
            'joinUri': f'https://welink.huaweicloud.com/j/{meeting_id}',
            'hostKey': 'test_host_key'
        }

    @staticmethod
    def create_mock_adapter():
        """Create a mock WeLink adapter."""
        adapter = Mock()
        adapter.create = Mock(return_value=MockWeLinkAPI.create_success_response())
        adapter.update = Mock(return_value={'updated': True})
        adapter.delete = Mock(return_value={'deleted': True})
        return adapter


class MockTencentAPI:
    """
    Mock Tencent Meeting API adapter for testing.

    Similar to MockZoomAPI but for Tencent-specific responses.
    """

    @staticmethod
    def create_success_response(meeting_id: str = "1234567890", meeting_code: str = "123456") -> Dict[str, Any]:
        """Generate successful Tencent meeting creation response."""
        return {
            'meeting_id': meeting_id,
            'meeting_code': meeting_code,
            'join_url': f'https://meeting.tencent.com/s/{meeting_code}',
            'hosts': [{'userid': 'test_host'}]
        }

    @staticmethod
    def create_mock_adapter():
        """Create a mock Tencent adapter."""
        adapter = Mock()
        adapter.create = Mock(return_value=MockTencentAPI.create_success_response())
        adapter.update = Mock(return_value={'updated': True})
        adapter.delete = Mock(return_value={'deleted': True})
        return adapter


# Assertion Helper Functions

def assert_notification_sent(mock_client, expected_count: int = 1):
    """
    Assert that notifications were sent.

    Args:
        mock_client: MockEmailClient or MockKafkaClient instance
        expected_count: Expected number of notifications
    """
    actual_count = mock_client.send_message.call_count if hasattr(mock_client, 'send_message') \
                   else mock_client.send_msg.call_count

    if actual_count != expected_count:
        raise AssertionError(
            f"Expected {expected_count} notifications, but {actual_count} were sent"
        )


def assert_cyclic_dates_correct(sub_meetings: List[Any], expected_dates: List[str]):
    """
    Verify that cyclic meeting sub-meeting dates are correct.

    Args:
        sub_meetings: List of MeetingCycleSubMeeting objects
        expected_dates: List of expected date strings (YYYY-MM-DD)
    """
    actual_dates = sorted([sm.date for sm in sub_meetings])
    expected_dates_sorted = sorted(expected_dates)

    if actual_dates != expected_dates_sorted:
        raise AssertionError(
            f"Sub-meeting dates don't match.\n"
            f"Expected: {expected_dates_sorted}\n"
            f"Actual: {actual_dates}"
        )


def assert_time_in_range(actual_time: str, expected_time: str, tolerance_minutes: int = 1):
    """
    Assert that a time is within tolerance of expected time.

    Useful for testing time-sensitive operations.

    Args:
        actual_time: Actual time string (HH:MM)
        expected_time: Expected time string (HH:MM)
        tolerance_minutes: Tolerance in minutes
    """
    def time_to_minutes(time_str: str) -> int:
        """Convert HH:MM to total minutes."""
        h, m = map(int, time_str.split(':'))
        return h * 60 + m

    actual_mins = time_to_minutes(actual_time)
    expected_mins = time_to_minutes(expected_time)
    diff = abs(actual_mins - expected_mins)

    if diff > tolerance_minutes:
        raise AssertionError(
            f"Time '{actual_time}' is not within {tolerance_minutes} minutes of '{expected_time}'"
        )


def assert_date_in_range(actual_date: str, start_date: str, end_date: str):
    """
    Assert that a date falls within a range.

    Args:
        actual_date: Date to check (YYYY-MM-DD)
        start_date: Range start (YYYY-MM-DD)
        end_date: Range end (YYYY-MM-DD)
    """
    from datetime import datetime

    actual = datetime.strptime(actual_date, "%Y-%m-%d").date()
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    end = datetime.strptime(end_date, "%Y-%m-%d").date()

    if not (start <= actual <= end):
        raise AssertionError(
            f"Date '{actual_date}' is not within range [{start_date}, {end_date}]"
        )


def assert_meeting_conflicts(meeting1: Dict[str, Any], meeting2: Dict[str, Any]) -> bool:
    """
    Check if two meetings have conflicting times.

    Args:
        meeting1: First meeting dict with 'date', 'start', 'end'
        meeting2: Second meeting dict with 'date', 'start', 'end'

    Returns:
        True if meetings conflict, False otherwise
    """
    # Different dates = no conflict
    if meeting1['date'] != meeting2['date']:
        return False

    # Same platform and community required for conflict
    if meeting1.get('platform') != meeting2.get('platform'):
        return False

    if meeting1.get('community') != meeting2.get('community'):
        return False

    def time_to_minutes(time_str: str) -> int:
        h, m = map(int, time_str.split(':'))
        return h * 60 + m

    m1_start = time_to_minutes(meeting1['start'])
    m1_end = time_to_minutes(meeting1['end'])
    m2_start = time_to_minutes(meeting2['start'])
    m2_end = time_to_minutes(meeting2['end'])

    # Check for overlap
    return not (m1_end <= m2_start or m2_end <= m1_start)


def generate_ics_content(meeting_data: Dict[str, Any]) -> str:
    """
    Generate ICS calendar content for a meeting.

    Useful for testing calendar invitation generation.

    Args:
        meeting_data: Meeting dictionary

    Returns:
        ICS formatted string
    """
    from datetime import datetime

    date_str = meeting_data['date']
    start_time = meeting_data['start']
    end_time = meeting_data['end']

    # Combine date and time
    start_dt = datetime.strptime(f"{date_str} {start_time}", "%Y-%m-%d %H:%M")
    end_dt = datetime.strptime(f"{date_str} {end_time}", "%Y-%m-%d %H:%M")

    # Format for ICS
    start_ics = start_dt.strftime("%Y%m%dT%H%M%S")
    end_ics = end_dt.strftime("%Y%m%dT%H%M%S")

    ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Meeting Platform//Test//EN
BEGIN:VEVENT
UID:{meeting_data.get('mid', 'test-meeting')}@test.com
DTSTAMP:{datetime.now().strftime("%Y%m%dT%H%M%S")}
DTSTART:{start_ics}
DTEND:{end_ics}
SUMMARY:{meeting_data['topic']}
DESCRIPTION:{meeting_data.get('agenda', '')}
LOCATION:{meeting_data.get('join_url', '')}
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR"""

    return ics


def create_mock_meeting_response(
    mid: str = "TEST123456",
    platform: str = "ZOOM",
    **overrides
) -> Dict[str, Any]:
    """
    Create a mock meeting API response.

    Args:
        mid: Meeting ID
        platform: Platform name
        **overrides: Additional fields to override

    Returns:
        Mock response dictionary
    """
    response = {
        'mid': mid,
        'platform': platform,
        'join_url': f'https://{platform.lower()}.test.com/j/{mid}',
        'host_id': 'test_host@test.com',
        'topic': 'Test Meeting',
        'date': str(datetime.date.today()),
        'start': '10:00',
        'end': '11:00',
        'is_record': True,
        'sponsor': 'TestUser',
        'group_name': 'test_group',
        'community': 'openEuler'
    }

    response.update(overrides)
    return response


class TestDataBuilder:
    """
    Builder pattern for constructing complex test data.

    Usage:
        meeting_data = (TestDataBuilder()
                       .with_platform('ZOOM')
                       .with_date_offset(days=7)
                       .with_recording(True)
                       .build())
    """

    def __init__(self):
        self.data = {
            "sponsor": "TestSponsor",
            "group_name": "test_group",
            "community": "openEuler",
            "topic": "Test Meeting",
            "platform": "WELINK",
            "date": str(datetime.date.today() + datetime.timedelta(days=1)),
            "start": "10:00",
            "end": "11:00",
            "etherpad": "https://etherpad.test.com/p/test",
            "agenda": "Test agenda",
            "email_list": "",
            "is_record": False
        }

    def with_platform(self, platform: str):
        """Set platform."""
        self.data['platform'] = platform
        return self

    def with_date_offset(self, days: int = 1):
        """Set date with offset from today."""
        self.data['date'] = str(datetime.date.today() + datetime.timedelta(days=days))
        return self

    def with_time(self, start: str, end: str):
        """Set meeting time."""
        self.data['start'] = start
        self.data['end'] = end
        return self

    def with_recording(self, is_record: bool = True):
        """Set recording flag."""
        self.data['is_record'] = is_record
        return self

    def with_topic(self, topic: str):
        """Set topic."""
        self.data['topic'] = topic
        return self

    def with_emails(self, emails: List[str]):
        """Set email list."""
        self.data['email_list'] = ';'.join(emails)
        return self

    def with_cyclic(self, cycle_type: int, interval: int, point: str, end_days: int = 30):
        """Make this a cyclic meeting."""
        self.data['is_cycle'] = True
        self.data['cycle_type'] = cycle_type
        self.data['interval'] = interval
        self.data['point'] = point
        self.data['start_date'] = self.data.pop('date')
        self.data['end_date'] = str(datetime.date.today() + datetime.timedelta(days=end_days))
        return self

    def build(self) -> Dict[str, Any]:
        """Build and return the data."""
        return self.data.copy()
