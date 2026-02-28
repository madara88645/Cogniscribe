"""
Tests for stt_service.py core logic.
"""

import sys
import types
from unittest.mock import MagicMock

import pytest

# ── Mock platform-specific modules before importing stt_service ───────────────

def _make_module(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod

sys.modules.setdefault("ctranslate2", _make_module("ctranslate2", get_cuda_device_count=MagicMock(return_value=0)))
sys.modules.setdefault("faster_whisper", _make_module("faster_whisper", WhisperModel=MagicMock()))

import stt_service

class TestDecodeQualityScore:
    def test_happy_path(self):
        """High confidence normal text should have a score close to confidence."""
        # This text is 4 words, 2 short tokens ('is', 'a'), ratio = 2/4 = 0.5
        # confidence = 0.9. _looks_fragmented is False because 0.5 >= 0.35, wait:
        # short_ratio >= 0.35 -> True. Oh.
        # Let's provide long words to prevent fragmentation logic.
        decoded = {
            "text": "understanding programming fundamentals",
            "confidence": 0.95
        }
        # tokens: understanding, programming, fundamentals (3 tokens)
        # short tokens: 0
        # fragment ratio: 0.0
        # looks_fragmented: < 4 tokens -> False.
        # score = 0.95 - 0.10 * 0.0 = 0.95
        assert stt_service._decode_quality_score(decoded) == pytest.approx(0.95)

    def test_looks_fragmented_penalty(self):
        """Text that looks fragmented should incur a 0.20 penalty."""
        # Needs >= 4 tokens and short_ratio >= 0.35 to be fragmented
        # tokens: a, b, c, longword (4 tokens)
        # short tokens: 3 (ratio 3/4 = 0.75 >= 0.35) -> True
        decoded = {
            "text": "a b c longword",
            "confidence": 0.8
        }
        # Score = 0.8 - 0.20 - 0.10 * 0.75 = 0.6 - 0.075 = 0.525
        assert stt_service._decode_quality_score(decoded) == pytest.approx(0.525)

    def test_missing_keys(self):
        """Missing 'text' and 'confidence' should default properly."""
        decoded = {}
        # text defaults to "", confidence to 0.0
        # _looks_fragmented("") returns True
        # _fragment_ratio("") returns 1.0
        # Score = 0.0 - 0.20 - 0.10 * 1.0 = -0.30
        assert stt_service._decode_quality_score(decoded) == pytest.approx(-0.30)

    def test_split_hint_penalty(self):
        """Text matching the split hint pattern should be marked as fragmented."""
        # Tokens: ip, le, mantasyon (3 tokens).
        # < 4 tokens -> _looks_fragmented returns False immediately.
        # Let's make it >= 4 tokens, but short_ratio < 0.35, yet contains hint pattern
        # "ip le mantasyon and another longword"
        # Tokens: ip(2), le(2), mantasyon(9), and(3), another(7), longword(8) -> 6 tokens
        # short tokens: ip, le -> 2. ratio: 2/6 = 0.333 < 0.35 -> doesn't trigger ratio
        # But split hint pattern matches -> True.
        decoded = {
            "text": "ip le mantasyon and another longword",
            "confidence": 0.90
        }
        # looks_fragmented: True (because of split hint)
        # fragment_ratio: 2/6 = 0.3333
        # Score = 0.90 - 0.20 - 0.10 * (2/6) = 0.70 - 0.03333 = 0.6666
        assert stt_service._decode_quality_score(decoded) == pytest.approx(0.90 - 0.20 - 0.10 * (2/6))

    def test_fragment_ratio_only(self):
        """Test fragment ratio calculation without looks_fragmented penalty."""
        # tokens < 4 -> _looks_fragmented returns False.
        # "a b longword" -> 3 tokens. short: a, b (2). ratio: 2/3
        decoded = {
            "text": "a b longword",
            "confidence": 0.80
        }
        # looks_fragmented: False
        # score = 0.80 - 0.10 * (2/3)
        assert stt_service._decode_quality_score(decoded) == pytest.approx(0.80 - 0.10 * (2/3))
