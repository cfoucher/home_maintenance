"""Tests for schedule calculation utilities."""

from datetime import datetime

import pytest
from freezegun import freeze_time

from custom_components.home_maintenance.schedule import (
    calculate_next_due,
    check_runtime_due,
    is_count_due,
)


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


class TestIsCountDue:
    """Tests for is_count_due."""

    def test_count_below_threshold_not_due(self):
        """current_count=3, threshold=5 → not due."""
        assert is_count_due(3, 5) is False

    def test_count_equals_threshold_due(self):
        """current_count=5, threshold=5 → due."""
        assert is_count_due(5, 5) is True

    def test_count_above_threshold_due(self):
        """current_count=10, threshold=5 → due."""
        assert is_count_due(10, 5) is True

    def test_count_threshold_zero_never_due(self):
        """threshold=0 disables count triggering."""
        assert is_count_due(100, 0) is False

    def test_count_threshold_negative_never_due(self):
        """Negative threshold treated as disabled."""
        assert is_count_due(5, -1) is False

    def test_count_zero_and_threshold_zero(self):
        """count=0, threshold=0 → not due."""
        assert is_count_due(0, 0) is False


class TestCheckRuntimeDue:
    """Tests for check_runtime_due."""

    def test_runtime_delta_below_threshold_not_due(self):
        """baseline=100, threshold=200, current=150 → delta=50, not due."""
        new_baseline, is_due = check_runtime_due(150.0, 100.0, 200.0)
        assert new_baseline == 100.0
        assert is_due is False

    def test_runtime_delta_equals_threshold_due(self):
        """baseline=100, threshold=200, current=300 → delta=200, due."""
        new_baseline, is_due = check_runtime_due(300.0, 100.0, 200.0)
        assert new_baseline == 100.0
        assert is_due is True

    def test_runtime_delta_above_threshold_due(self):
        """baseline=100, threshold=200, current=400 → delta=300, due."""
        new_baseline, is_due = check_runtime_due(400.0, 100.0, 200.0)
        assert new_baseline == 100.0
        assert is_due is True

    def test_runtime_external_reset(self):
        """baseline=100, threshold=200, current=50 → baseline resets to 50, not due."""
        new_baseline, is_due = check_runtime_due(50.0, 100.0, 200.0)
        assert new_baseline == 50.0  # Reset to current value
        assert is_due is False

    def test_runtime_zero_threshold_never_due(self):
        """threshold=0 disables runtime triggering."""
        new_baseline, is_due = check_runtime_due(500.0, 100.0, 0.0)
        assert is_due is False

    def test_runtime_negative_threshold_never_due(self):
        """Negative threshold treated as disabled."""
        new_baseline, is_due = check_runtime_due(500.0, 100.0, -10.0)
        assert is_due is False

    def test_runtime_reset_then_new_baseline(self):
        """After reset (50 < 100), new baseline=50. Then further value delta from new base."""
        new_baseline, is_due = check_runtime_due(50.0, 100.0, 30.0)
        assert new_baseline == 50.0
        assert is_due is False

        # Now use the new baseline
        new_baseline2, is_due2 = check_runtime_due(90.0, new_baseline, 30.0)
        assert new_baseline2 == 50.0
        assert is_due2 is True  # 90 - 50 = 40 >= 30

    def test_runtime_identical_value_not_due(self):
        """Value equal to baseline → delta=0, not due."""
        new_baseline, is_due = check_runtime_due(100.0, 100.0, 50.0)
        assert new_baseline == 100.0
        assert is_due is False
