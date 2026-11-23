"""Tests for the watering prediction."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from custom_components.plant.prediction import predict_dry_time

NOW = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)


def _hourly(
    start_value: float, step: float, count: int, last_time: datetime
) -> list[tuple[datetime, float]]:
    """`count` hourly readings ending at `last_time`, changing by `step` per hour."""
    return [
        (last_time - timedelta(hours=count - 1 - index), start_value + step * index)
        for index in range(count)
    ]


def test_steady_drydown() -> None:
    readings = _hourly(40.0, -0.5, 49, NOW)

    assert predict_dry_time(readings, 15.0, NOW) == NOW + timedelta(hours=2)


def test_watering_inside_window_uses_only_later_readings() -> None:
    before = _hourly(30.0, -0.5, 25, NOW - timedelta(hours=25))
    after = _hourly(45.0, -0.4, 25, NOW)

    result = predict_dry_time(before + after, 15.0, NOW)

    # The fit runs over the 24 readings after the jump: 44.6 down to 35.4
    assert result == NOW + timedelta(hours=(35.4 - 15.0) / 0.4)


def test_readings_older_than_the_window_are_ignored() -> None:
    old = _hourly(80.0, 0.0, 10, NOW - timedelta(hours=200))
    recent = _hourly(40.0, -0.5, 49, NOW)

    assert predict_dry_time(old + recent, 15.0, NOW) == NOW + timedelta(hours=2)


@pytest.mark.parametrize("step", [0.0, 0.3])
def test_rising_or_flat_returns_none(step: float) -> None:
    readings = _hourly(30.0, step, 30, NOW)

    assert predict_dry_time(readings, 15.0, NOW) is None


def test_too_few_readings_returns_none() -> None:
    readings = [
        (NOW - timedelta(hours=4 * (4 - index)), 40.0 - 2 * index) for index in range(5)
    ]

    assert predict_dry_time(readings, 15.0, NOW) is None


def test_too_short_span_returns_none() -> None:
    readings = [
        (NOW - timedelta(minutes=40 * (9 - index)), 40.0 - index) for index in range(10)
    ]

    assert predict_dry_time(readings, 15.0, NOW) is None


def test_already_below_minimum_returns_now() -> None:
    readings = _hourly(20.0, -0.5, 30, NOW)

    assert predict_dry_time(readings, 15.0, NOW) == NOW
