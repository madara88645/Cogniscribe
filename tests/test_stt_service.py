"""
Tests for stt_service.py core logic.
"""

import math
import sys
import types
from unittest.mock import MagicMock

import pytest

# ── Mock ML dependencies before importing stt_service ───────────────


def _make_module(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


sys.modules.setdefault("ctranslate2", _make_module("ctranslate2"))
sys.modules.setdefault(
    "faster_whisper", _make_module("faster_whisper", WhisperModel=MagicMock())
)

import stt_service  # noqa: E402


class TestConfidenceScore:
    def test_perfect_score(self):
        """When avg_logprob is 0.0 and no_speech_prob is 0.0, score should be 1.0"""
        score = stt_service._confidence_score(0.0, 0.0)
        assert score == pytest.approx(1.0)

    def test_worst_score(self):
        """When avg_logprob is low and no_speech_prob is 1.0, score should be near 0"""
        score = stt_service._confidence_score(-100.0, 1.0)
        # lp_conf approaches 0, speech_conf is 0.
        assert score == pytest.approx(0.0, abs=1e-5)

    def test_out_of_bounds_positive(self):
        """Should cap inputs correctly if they exceed expected bounds."""
        # avg_logprob capped at 0.0 (exp(0) = 1.0)
        # no_speech_prob capped at 1.0 (1.0 - 1.0 = 0.0)
        # 0.6 * 1.0 + 0.4 * 0.0 = 0.6
        score = stt_service._confidence_score(5.0, 2.0)
        assert score == pytest.approx(0.6)

    def test_out_of_bounds_negative(self):
        """Should floor inputs correctly if they are below expected bounds."""
        # avg_logprob is low (exp(-100) ~ 0.0)
        # no_speech_prob floored at 0.0 (1.0 - 0.0 = 1.0)
        # 0.6 * 0.0 + 0.4 * 1.0 = 0.4
        score = stt_service._confidence_score(-100.0, -1.0)
        assert score == pytest.approx(0.4, abs=1e-5)

    def test_mid_score(self):
        """Test a realistic mid-range confidence score."""
        # avg_logprob = -0.5 -> exp(-0.5) ~ 0.60653
        # no_speech_prob = 0.2 -> 1.0 - 0.2 = 0.8
        # 0.6 * 0.60653 + 0.4 * 0.8 = 0.363918 + 0.320 = 0.683918
        score = stt_service._confidence_score(-0.5, 0.2)
        expected = 0.6 * math.exp(-0.5) + 0.4 * 0.8
        assert score == pytest.approx(expected)
