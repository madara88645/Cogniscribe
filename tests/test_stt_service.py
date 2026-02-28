"""Tests for STT service internal functions."""

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

from stt_service import _looks_fragmented


class TestLooksFragmented:
    def test_empty_string(self):
        """Empty string or None should be treated as fragmented."""
        assert _looks_fragmented("") is True
        assert _looks_fragmented(None) is True

    def test_few_tokens(self):
        """Strings with fewer than 4 tokens are generally not considered fragmented (unless empty)."""
        assert _looks_fragmented("one") is False
        assert _looks_fragmented("one two") is False
        assert _looks_fragmented("one two three") is False

    def test_high_short_ratio(self):
        """If 35% or more of the tokens are short (length <= 2), it's fragmented."""
        # 4 tokens: "a", "b", "cd", "ef" -> 2 short out of 4 (50%)
        assert _looks_fragmented("a b cd ef") is True
        # 5 tokens: "a", "b", "cde", "fgh", "ijk" -> 2 short out of 5 (40%)
        assert _looks_fragmented("a b cde fgh ijk") is True

    def test_low_short_ratio(self):
        """If less than 35% of the tokens are short, it's not fragmented."""
        # 4 tokens: "a", "bcd", "efg", "hij" -> 1 short out of 4 (25%)
        assert _looks_fragmented("a bcd efg hij") is False
        # 5 tokens: "a", "bcd", "efg", "hij", "klm" -> 1 short out of 5 (20%)
        assert _looks_fragmented("a bcd efg hij klm") is False

    def test_split_hint_present(self):
        """Specific split hints like 'ip le mantasyon' should mark as fragmented."""
        # Ratio is low: 0 short out of 4 tokens (0%)
        # Tokens: "some", "ip", "le", "mantasyon" -> 2 short ("ip", "le") out of 4 (50%). Wait, if it has short it will trigger short ratio.
        # We need a low ratio string that includes the hint to test the regex fallback.
        # "ip le mantasyon" -> 2 short, 1 long = 2/3 = 66% (Wait, length is 3, so few tokens? < 4 tokens -> False? Let's check: len(tokens)<4 returns False before ratio or hint!)
        # Let's ensure length >= 4.
        # "test one ip le mantasyon here longword anotherword" ->
        # tokens: test, one, ip, le, mantasyon, here, longword, anotherword (8 tokens)
        # short: ip, le (2)
        # ratio: 2/8 = 25% (< 35%)
        assert _looks_fragmented("test one ip le mantasyon here longword anotherword") is True

        # Test with turkish i
        assert _looks_fragmented("test one ıp le mantasyon here longword anotherword") is True

    def test_no_split_hint_present(self):
        """If ratio is low and no split hint is present, it's not fragmented."""
        assert _looks_fragmented("test one implementation here longword anotherword") is False
