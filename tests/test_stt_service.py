"""Tests for the stt_service module."""

import sys
import types
from unittest.mock import MagicMock

import pytest


def _make_module(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


sys.modules.setdefault("ctranslate2", _make_module("ctranslate2"))
sys.modules.setdefault(
    "faster_whisper", _make_module("faster_whisper", WhisperModel=MagicMock())
)

from stt_service import _fragment_ratio


class TestFragmentRatio:
    def test_empty_string(self):
        """Empty string should return 1.0 (100% fragmented)."""
        assert _fragment_ratio("") == 1.0

    def test_none_input(self):
        """None input should be treated as empty and return 1.0."""
        assert _fragment_ratio(None) == 1.0  # type: ignore[arg-type]

    def test_no_valid_tokens(self):
        """String with only punctuation or spaces should return 1.0."""
        assert _fragment_ratio("! @ # $ %") == 1.0
        assert _fragment_ratio("   ") == 1.0

    def test_all_short_tokens(self):
        """String with only tokens of length <= 2 should return 1.0."""
        assert _fragment_ratio("a b cd e f") == 1.0

    def test_no_short_tokens(self):
        """String with only tokens of length > 2 should return 0.0."""
        assert _fragment_ratio("hello world testing") == 0.0

    def test_mixed_tokens(self):
        """String with mixed length tokens should return correct ratio."""
        # 4 tokens total: "hi" (2), "there" (5), "my" (2), "friend" (6)
        # 2 short tokens ("hi", "my") -> ratio = 2 / 4 = 0.5
        assert _fragment_ratio("hi there my friend") == 0.5

        # 5 tokens total: "a" (1), "bc" (2), "def" (3), "ghij" (4), "k" (1)
        # 3 short tokens ("a", "bc", "k") -> ratio = 3 / 5 = 0.6
        assert _fragment_ratio("a bc def ghij k") == 0.6

    def test_turkish_characters(self):
        """Should correctly identify tokens with Turkish characters."""
        # "çö" (2), "ğü" (2), "ış" (2) - all short
        assert _fragment_ratio("çö ğü ış") == 1.0

        # "çalışmak" (8), "güzeldir" (8) - all long
        assert _fragment_ratio("çalışmak güzeldir") == 0.0

        # "o" (1), "zaman" (5), "iş" (2), "böyle" (5)
        # 4 tokens, 2 short ("o", "iş") -> ratio = 0.5
        assert _fragment_ratio("o zaman iş böyle") == 0.5

    def test_mixed_case(self):
        """Case should not affect token length calculation."""
        # "I" (1), "AM" (2), "SHOUTING" (8)
        # 3 tokens, 2 short ("I", "AM") -> ratio = 2 / 3 = 0.666...
        assert _fragment_ratio("I AM SHOUTING") == pytest.approx(2 / 3)
