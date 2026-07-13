"""Tests for schedule calculation utilities."""

from datetime import datetime

import pytest
from freezegun import freeze_time

from custom_components.home_maintenance.schedule import calculate_next_due


class TestCalculateNextDue:
    """Tests for calculate_next_due."""

    def test_calculate_next_due_days(self):
        """Last performed + 90 days."""
        last = datetime(2025, 1, 1, 12, 0, 0)
        result = calculate_next_due(last, 90, "days")
        assert result == datetime(2025, 4, 1, 12, 0, 0)

    def test_calculate_next_due_weeks(self):
        """Last performed + 2 weeks."""
        last = datetime(2025, 1, 1, 12, 0, 0)
        result = calculate_next_due(last, 2, "weeks")
        assert result == datetime(2025, 1, 15, 12, 0, 0)

    def test_calculate_next_due_months(self):
        """Last performed + 1 month."""
        last = datetime(2025, 1, 15, 12, 0, 0)
        result = calculate_next_due(last, 1, "months")
        assert result == datetime(2025, 2, 15, 12, 0, 0)

    def test_calculate_next_due_month_end(self):
        """Jan 31 + 1 month -> Feb 28 (relativedelta clamps correctly)."""
        last = datetime(2025, 1, 31, 12, 0, 0)
        result = calculate_next_due(last, 1, "months")
        # relativedelta(months=1) from Jan 31 yields Feb 28 (non-leap year 2025)
        assert result == datetime(2025, 2, 28, 12, 0, 0)

    def test_calculate_next_due_month_end_leap_year(self):
        """Jan 31 + 1 month in a leap year -> Feb 29."""
        last = datetime(2024, 1, 31, 12, 0, 0)
        result = calculate_next_due(last, 1, "months")
        assert result == datetime(2024, 2, 29, 12, 0, 0)

    def test_calculate_next_due_unknown_type_returns_last(self):
        """Unknown interval type returns last_performed unchanged."""
        last = datetime(2025, 1, 15, 12, 0, 0)
        result = calculate_next_due(last, 30, "years")
        assert result == last

    def test_calculate_next_due_preserves_time(self):
        """Time component is preserved (caller may zero it after)."""
        last = datetime(2025, 6, 15, 8, 30, 45)
        result = calculate_next_due(last, 14, "days")
        assert result == datetime(2025, 6, 29, 8, 30, 45)
