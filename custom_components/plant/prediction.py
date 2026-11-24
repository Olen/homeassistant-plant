"""Predict when a plant's soil will have dried out, from its moisture readings."""

from __future__ import annotations

from datetime import datetime, timedelta

from .const import (
    MOISTURE_INCREASE_THRESHOLD,
    PREDICTION_MIN_READINGS,
    PREDICTION_MIN_SPAN,
    PREDICTION_WINDOW,
)

SECONDS_PER_HOUR = 3600


def _readings_since_last_watering(
    readings: list[tuple[datetime, float]],
) -> list[tuple[datetime, float]]:
    """The readings after the last jump of MOISTURE_INCREASE_THRESHOLD or more."""
    start = 0
    for index in range(1, len(readings)):
        rise = readings[index][1] - readings[index - 1][1]
        if rise >= MOISTURE_INCREASE_THRESHOLD:
            start = index + 1
    return readings[start:]


def _slope_per_hour(readings: list[tuple[datetime, float]]) -> float:
    """Least-squares slope of the values over time, in percent per hour."""
    first_time = readings[0][0]
    hours = [
        (time - first_time).total_seconds() / SECONDS_PER_HOUR for time, _ in readings
    ]
    values = [value for _, value in readings]
    mean_hours = sum(hours) / len(hours)
    mean_value = sum(values) / len(values)
    covariance = 0.0
    variance = 0.0
    for hour, value in zip(hours, values, strict=True):
        covariance += (hour - mean_hours) * (value - mean_value)
        variance += (hour - mean_hours) ** 2
    return covariance / variance


def predict_dry_time(
    readings: list[tuple[datetime, float]], minimum: float, now: datetime
) -> datetime | None:
    """When the moisture reaches `minimum`, or None without a clear dry-down."""
    recent = sorted(
        (reading for reading in readings if reading[0] >= now - PREDICTION_WINDOW),
        key=lambda reading: reading[0],
    )
    since_watering = _readings_since_last_watering(recent)
    if len(since_watering) < PREDICTION_MIN_READINGS:
        return None
    if since_watering[-1][0] - since_watering[0][0] < PREDICTION_MIN_SPAN:
        return None

    slope = _slope_per_hour(since_watering)
    if slope >= 0:
        return None

    latest_time, latest = since_watering[-1]
    if latest <= minimum:
        return now
    # The drying continues from the last reading, which may be hours old
    dry_time = latest_time + timedelta(hours=(latest - minimum) / -slope)
    return max(dry_time, now)
