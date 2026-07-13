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
