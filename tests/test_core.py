"""Basic smoke tests for config_manager and audio_processing."""

import copy
from typing import Any

import numpy as np
import pytest

from audio_processing import get_rms, preprocess_audio_bytes
from config_manager import (
    DEFAULT_CONFIG,
    _coerce_language,
    _deep_merge,
    _sanitize_hints,
    get_profile_decode_options,
    load_config,
)


class TestDeepMerge:
    def test_shallow_override(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3}

    def test_nested_merge(self):
        base = {"stt": {"model_cpu": "small", "device": "auto"}}
        override = {"stt": {"model_cpu": "medium"}}
        result = _deep_merge(base, override)
        assert result["stt"]["model_cpu"] == "medium"
        assert result["stt"]["device"] == "auto"

    def test_does_not_mutate_base(self):
        base = {"x": {"y": 1}}
        override = {"x": {"y": 2}}
        _deep_merge(base, override)
        assert base["x"]["y"] == 1


class TestCoerceLanguage:
    def test_simple(self):
        assert _coerce_language("tr") == "tr"

    def test_locale_with_region(self):
        assert _coerce_language("tr-TR") == "tr"

    def test_uppercase(self):
        assert _coerce_language("EN") == "en"

    def test_non_string(self):
        assert _coerce_language(42) == "tr"  # type: ignore[arg-type]


class TestSanitizeHints:
    def test_basic(self):
        hints = ["Proje", "  API  ", "deployment"]
        result = _sanitize_hints(hints)
        assert result == ["proje", "api", "deployment"]

    def test_non_list(self):
        assert _sanitize_hints("not a list") == []

    def test_skips_non_strings(self):
        assert _sanitize_hints([1, "valid", None]) == ["valid"]

    def test_max_32(self):
        hints = [str(i) for i in range(50)]
        assert len(_sanitize_hints(hints)) == 32


class TestGetProfileDecodeOptions:
    def test_balanced_profile(self):
        config = _make_config("balanced")
        opts = get_profile_decode_options(config)
        assert opts["beam_size"] == 3
        assert opts["best_of"] == 3
        assert opts["vad_filter"] is True

    def test_fast_profile(self):
        config = _make_config("fast")
        opts = get_profile_decode_options(config)
        assert opts["beam_size"] == 1

    def test_quality_profile(self):
        config = _make_config("quality")
        opts = get_profile_decode_options(config)
        assert opts["beam_size"] == 5

    def test_unknown_profile_falls_back_to_balanced(self):
        config = _make_config("nonexistent")
        opts = get_profile_decode_options(config)
        assert opts["beam_size"] == 3

    def test_legacy_decode_uses_stt_values(self):
        config = _make_config("balanced")
        config["stt"]["use_legacy_decode_values"] = True
        config["stt"]["beam_size"] = 7
        opts = get_profile_decode_options(config)
        assert opts["beam_size"] == 7


def _make_config(profile: str) -> dict[str, Any]:
    cfg: dict[str, Any] = copy.deepcopy(DEFAULT_CONFIG)
    cfg["stt"]["quality_profile"] = profile
    return cfg


class TestGetRms:
    def test_silence(self):
        data = np.zeros(1024, dtype=np.int16)
        assert get_rms(data) == 0.0

    def test_empty(self):
        data = np.array([], dtype=np.int16)
        assert get_rms(data) == 0.0

    def test_positive_value(self):
        data = np.full(100, 1000, dtype=np.int16)
        assert get_rms(data) == pytest.approx(1000.0)


class TestPreprocessAudioBytes:
    def test_returns_bytes(self):
        data = np.zeros(1600, dtype=np.int16)
        raw = data.tobytes()
        result = preprocess_audio_bytes(
            audio_bytes=raw,
            sample_rate=16000,
            highpass_hz=80.0,
            normalize_target_dbfs=-20.0,
            noise_suppression=False,
        )
        assert isinstance(result, bytes)

    def test_length_preserved(self):
        data = np.zeros(1600, dtype=np.int16)
        raw = data.tobytes()
        result = preprocess_audio_bytes(
            audio_bytes=raw,
            sample_rate=16000,
            highpass_hz=0.0,
            normalize_target_dbfs=-20.0,
            noise_suppression=False,
        )
        assert len(result) == len(raw)


class TestLoadConfig:
    def test_returns_dict(self):
        cfg = load_config()
        assert isinstance(cfg, dict)

    def test_has_required_keys(self):
        cfg = load_config()
        for key in ("hotkey", "exit_hotkey", "stt", "audio", "telemetry"):
            assert key in cfg

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("VOICE_PASTE_STT__DEVICE", "cpu")
        cfg = load_config()
        assert cfg["stt"]["device"] == "cpu"
