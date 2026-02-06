#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2026 Huawei Technologies Co., Ltd.
"""
Test fixtures and data factories for meeting tests.

This module provides reusable test data generators to eliminate code duplication
and maintain consistency across test suites.
"""
import datetime
from datetime import timedelta
from typing import Optional, Dict, Any, List


def get_future_date(days: int = 1) -> str:
    """
    Get a future date as a string.

    Args:
        days: Number of days from today (default: 1)

    Returns:
        Date string in format 'YYYY-MM-DD'
    """
    future_date = datetime.datetime.now().date() + timedelta(days=days)
    return str(future_date)


def get_past_date(days: int = 1) -> str:
    """
    Get a past date as a string.

    Args:
        days: Number of days before today (default: 1)

    Returns:
        Date string in format 'YYYY-MM-DD'
    """
    past_date = datetime.datetime.now().date() - timedelta(days=days)
    return str(past_date)


def get_date_range(start_days: int, end_days: int) -> tuple:
    """
    Get a date range relative to today.

    Args:
        start_days: Number of days from today for start date
        end_days: Number of days from today for end date

    Returns:
        Tuple of (start_date_str, end_date_str)
    """
    return get_future_date(start_days), get_future_date(end_days)


def create_test_meeting_data(overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Generate standard meeting test data with optional overrides.

    This is the primary factory for single (non-cyclic) meeting test data.

    Args:
        overrides: Dictionary of field values to override defaults

    Returns:
        Dictionary of meeting data ready for API calls

    Example:
        >>> data = create_test_meeting_data({'topic': 'Custom Topic', 'platform': 'zoom'})
        >>> response = client.post('/inner/v1/meeting/meeting/', data=data)
    """
    default_data = {
        "sponsor": "Tom",
        "group_name": "group_temp",
        "community": "openEuler",
        "topic": "meeting unitest create topic",
        "platform": "welink",  # Must be lowercase to match COMMUNITY_HOST keys
        "date": get_future_date(1),
        "start": "08:00",
        "end": "09:00",
        "etherpad": "https://etherpad.test.com/p/infrastructure",
        "agenda": "今天开个会议",
        "email_list": "",
        "is_record": True
    }

    if overrides:
        default_data.update(overrides)

    return default_data


def create_cyclic_meeting_data(
    cycle_type: int,
    interval: int,
    point: str,
    start_days: int = 1,
    end_days: int = 30,
    overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate cyclic meeting test data with specified cycle parameters.

    Args:
        cycle_type: Cycle type (0=daily, 1=weekly, 2=monthly)
        interval: Interval between meetings (e.g., 1=every day, 2=every 2 days)
        point: Cycle points (e.g., "1,3,5" for weekly Mon/Wed/Fri, "1,15" for monthly 1st and 15th)
        start_days: Days from today for start date (default: 1)
        end_days: Days from today for end date (default: 30)
        overrides: Dictionary of additional field overrides

    Returns:
        Dictionary of cyclic meeting data ready for API calls

    Examples:
        >>> # Daily meeting every day for 30 days
        >>> data = create_cyclic_meeting_data(cycle_type=0, interval=1, point="1")

        >>> # Weekly meeting on Mon/Wed/Fri for 60 days
        >>> data = create_cyclic_meeting_data(cycle_type=1, interval=1, point="1,3,5", end_days=60)

        >>> # Monthly meeting on 1st and 15th for 90 days
        >>> data = create_cyclic_meeting_data(cycle_type=2, interval=1, point="1,15", end_days=90)
    """
    start_date, end_date = get_date_range(start_days, end_days)

    default_data = {
        "sponsor": "Tom",
        "group_name": "group_temp",
        "community": "openEuler",
        "topic": "cyclic meeting unitest topic",
        "platform": "welink",  # Changed to lowercase - only welink supports cyclic meetings
        "is_cycle": True,
        "cycle_type": cycle_type,
        "cycle_start_date": start_date,
        "cycle_end_date": end_date,
        "cycle_start": "08:00",  # Use cycle_start for cyclic meetings
        "cycle_end": "09:00",    # Use cycle_end for cyclic meetings
        "cycle_interval": interval,  # Use cycle_interval instead of interval
        "cycle_point": point,        # Use cycle_point instead of point
        "etherpad": "https://etherpad.test.com/p/cyclic",
        "agenda": "周期性会议议程",
        "email_list": "",
        "is_record": True
    }

    if overrides:
        default_data.update(overrides)

    return default_data


def create_daily_cycle_data(
    interval: int = 1,
    duration_days: int = 30,
    overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience factory for daily cyclic meetings.

    Args:
        interval: Days between meetings (1=daily, 2=every 2 days, etc.)
        duration_days: Total duration of cycle in days
        overrides: Additional field overrides

    Returns:
        Dictionary of daily cyclic meeting data
    """
    return create_cyclic_meeting_data(
        cycle_type=0,
        interval=interval,
        point="1",
        end_days=duration_days,
        overrides=overrides
    )


def create_weekly_cycle_data(
    weekdays: List[int] = None,
    interval: int = 1,
    duration_days: int = 56,
    overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience factory for weekly cyclic meetings.

    Args:
        weekdays: List of weekday numbers (1=Mon, 2=Tue, ..., 7=Sun). Default: [1] (Monday)
        interval: Weeks between meetings (1=every week, 2=every 2 weeks, etc.)
        duration_days: Total duration of cycle in days
        overrides: Additional field overrides

    Returns:
        Dictionary of weekly cyclic meeting data

    Examples:
        >>> # Every Monday
        >>> data = create_weekly_cycle_data(weekdays=[1])

        >>> # Mon, Wed, Fri every week
        >>> data = create_weekly_cycle_data(weekdays=[1, 3, 5])

        >>> # Every 2 weeks on Tuesday
        >>> data = create_weekly_cycle_data(weekdays=[2], interval=2)
    """
    if weekdays is None:
        weekdays = [1]

    point = ",".join(str(d) for d in weekdays)

    return create_cyclic_meeting_data(
        cycle_type=1,
        interval=interval,
        point=point,
        end_days=duration_days,
        overrides=overrides
    )


def create_monthly_cycle_data(
    days_of_month: List[int] = None,
    interval: int = 1,
    duration_days: int = 90,
    overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Convenience factory for monthly cyclic meetings.

    Args:
        days_of_month: List of days in month (1-31). Default: [1] (1st of month)
        interval: Months between meetings (1=every month, 2=every 2 months, etc.)
        duration_days: Total duration of cycle in days
        overrides: Additional field overrides

    Returns:
        Dictionary of monthly cyclic meeting data

    Examples:
        >>> # 1st of every month
        >>> data = create_monthly_cycle_data(days_of_month=[1])

        >>> # 1st and 15th of every month
        >>> data = create_monthly_cycle_data(days_of_month=[1, 15])

        >>> # Last day of every month (31 will fall back to last day in short months)
        >>> data = create_monthly_cycle_data(days_of_month=[31])
    """
    if days_of_month is None:
        days_of_month = [1]

    point = ",".join(str(d) for d in days_of_month)

    return create_cyclic_meeting_data(
        cycle_type=2,
        interval=interval,
        point=point,
        end_days=duration_days,
        overrides=overrides
    )


def create_test_user_data(username: Optional[str] = None) -> Dict[str, str]:
    """
    Generate test user data.

    Args:
        username: Optional username override (auto-generated if not provided)

    Returns:
        Dictionary with user data
    """
    if username is None:
        import secrets
        username = f"testuser_{secrets.token_hex(4)}"

    return {
        "username": username,
        "password": "testpass123",
        "email": f"{username}@test.com"
    }


def create_minimal_meeting_data() -> Dict[str, Any]:
    """
    Create minimal valid meeting data (only required fields).

    Useful for testing validation and ensuring minimum requirements.

    Returns:
        Dictionary with only required fields
    """
    return {
        "sponsor": "MinimalSponsor",
        "group_name": "minimal_group",
        "community": "openEuler",
        "topic": "Minimal Meeting",
        "platform": "welink",
        "date": get_future_date(1),
        "start": "10:00",
        "end": "11:00",
        "etherpad": "",
        "agenda": "",
        "email_list": "",
        "is_record": False
    }


def create_maximal_meeting_data() -> Dict[str, Any]:
    """
    Create meeting data with all optional fields populated.

    Useful for testing comprehensive data handling.

    Returns:
        Dictionary with all fields populated
    """
    return {
        "sponsor": "MaximalSponsor",
        "group_name": "maximal_group",
        "community": "openEuler",
        "topic": "Maximal Meeting with All Fields",
        "platform": "zoom",
        "date": get_future_date(7),
        "start": "14:00",
        "end": "16:00",
        "etherpad": "https://etherpad.test.com/p/maximal-meeting",
        "agenda": "详细的会议议程，包含多个议题:\n1. 第一个议题\n2. 第二个议题\n3. 第三个议题",
        "email_list": "user1@test.com;user2@test.com;user3@test.com",
        "is_record": True
    }


def create_platform_specific_data(platform: str) -> Dict[str, Any]:
    """
    Create meeting data for specific platform (zoom, welink, tencent).

    Args:
        platform: Platform name ('zoom', 'welink', or 'tencent')

    Returns:
        Dictionary configured for the specified platform
    """
    return create_test_meeting_data({
        "platform": platform,
        "topic": f"{platform} Platform Test Meeting"
    })


def create_conflicting_meeting_data(existing_date: str, existing_start: str, existing_end: str) -> Dict[str, Any]:
    """
    Create meeting data that will conflict with an existing meeting.

    Useful for testing conflict detection logic.

    Args:
        existing_date: Date of existing meeting
        existing_start: Start time of existing meeting
        existing_end: End time of existing meeting

    Returns:
        Dictionary with overlapping time
    """
    return create_test_meeting_data({
        "date": existing_date,
        "start": existing_start,
        "end": existing_end,
        "topic": "Conflicting Meeting"
    })


# Validation test data
INVALID_XSS_STRINGS = [
    "<script>alert('xss')</script>",
    "<img src=x onerror=alert('xss')>",
    "javascript:alert('xss')"
]

INVALID_CRLF_STRINGS = [
    "test\r\ninjection",
    "test\rinjection",
    "test\ninjection"
]

INVALID_HTTP_STRINGS = [
    "http://malicious.com",
    "https://malicious.com",
    "ftp://malicious.com"
]

INVALID_LONG_STRINGS = {
    "sponsor_too_long": "a" * 65,
    "group_name_too_long": "g" * 65,
    "topic_too_long": "t" * 129,
    "etherpad_too_long": "https://test.com/" + "e" * 240,
    "agenda_too_long": "a" * 4097,
    "email_list_too_long": "e" * 1001
}
