"""Tests for UTC-aware datetime helpers."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from datetime_utils import as_utc, utc_now


def test_utc_now_is_timezone_aware():
    now = utc_now()
    assert now.tzinfo is not None
    assert now.utcoffset() == timedelta(0)


def test_as_utc_treats_naive_as_utc():
    naive = datetime(2026, 1, 2, 3, 4, 5)
    aware = as_utc(naive)
    assert aware.tzinfo == timezone.utc
    assert aware.replace(tzinfo=None) == naive


def test_as_utc_converts_other_offsets():
    eastern = timezone(timedelta(hours=-5))
    value = datetime(2026, 1, 2, 12, 0, 0, tzinfo=eastern)
    converted = as_utc(value)
    assert converted.tzinfo == timezone.utc
    assert converted.hour == 17
