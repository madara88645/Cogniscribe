"""Tests for stt_service.py."""

import pytest
from stt_service import _mean

class TestMean:
    def test_mean_valid_numbers(self):
        assert _mean([1, 2, 3], 0.0) == 2.0
        assert _mean([1.5, 2.5], 0.0) == 2.0

    def test_mean_string_numbers(self):
        assert _mean(["1", "2.5"], 0.0) == 1.75

    def test_mean_with_none_values(self):
        assert _mean([1, None, 3, None], 0.0) == 2.0

    def test_mean_all_none_returns_default(self):
        assert _mean([None, None], 10.0) == 10.0

    def test_mean_empty_list_returns_default(self):
        assert _mean([], 5.0) == 5.0

    def test_mean_with_zeros(self):
        assert _mean([0, 0, 0], 1.0) == 0.0

    def test_mean_invalid_string_raises_value_error(self):
        with pytest.raises(ValueError):
            _mean(["not_a_number"], 0.0)
