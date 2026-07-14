"""Schedule calculation utilities for Home Maintenance."""

from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta


def calculate_next_due(
    last_performed: datetime, interval_value: int, interval_type: str
) -> datetime:
    """Calculate the next date based on last date and interval."""
    if interval_type == "days":
        return last_performed + timedelta(days=interval_value)
    if interval_type == "weeks":
        return last_performed + timedelta(weeks=interval_value)
    if interval_type == "months":
        return last_performed + relativedelta(months=interval_value)

    return last_performed


def is_count_due(current_count: int, threshold: int) -> bool:
    """
    Check if a count-based task is due.

    Returns True if current_count >= threshold (and threshold > 0).
    Returns False if threshold is 0 (no threshold configured).
    """
    if threshold <= 0:
        return False
    return current_count >= threshold


def check_runtime_due(
    current_value: float, baseline: float, threshold: float
) -> tuple[float, bool]:
    """
    Check if a runtime-based task is due.

    Detects external resets (when current_value drops below baseline)
    and resets baseline accordingly.

    Returns (new_baseline, is_due). The caller should persist the
    new_baseline if it changed.
    """
    # External reset detected — sensor value dropped below baseline
    baseline = min(baseline, current_value)

    delta = current_value - baseline
    if threshold <= 0:
        return baseline, False
    return baseline, delta >= threshold
