"""
Tests for voice_paste.py core logic.

All platform-specific and hardware-dependent modules (winsound, pyaudio,
pyautogui, pyperclip, keyboard, faster_whisper) are mocked at the module
level so these tests run on any OS without special hardware.
"""

import io
import json
import os
import sys
import types
import wave
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ── Mock platform-specific modules before importing voice_paste ───────────────


def _make_module(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


sys.modules.setdefault("winsound", _make_module("winsound", Beep=MagicMock()))
sys.modules.setdefault("pyaudio", _make_module("pyaudio", PyAudio=MagicMock, paInt16=8))
sys.modules.setdefault(
    "pyautogui", _make_module("pyautogui", hotkey=MagicMock(), press=MagicMock())
)
sys.modules.setdefault("pyperclip", _make_module("pyperclip", copy=MagicMock()))
sys.modules.setdefault(
    "keyboard", _make_module("keyboard", add_hotkey=MagicMock(), wait=MagicMock())
)
sys.modules.setdefault(
    "faster_whisper", _make_module("faster_whisper", WhisperModel=MagicMock())
)

import voice_paste  # noqa: E402  (must come after mocking)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_wav_bytes(num_frames: int = 1600, sample_rate: int = 16000) -> bytes:
    """Return a minimal valid WAV byte-string filled with silence."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_frames)
    return buf.getvalue()


# ── Config tests ──────────────────────────────────────────────────────────────


class TestLoadConfig:
    def test_returns_defaults_when_no_file(self, tmp_path, monkeypatch):
        """load_config() returns a copy of DEFAULT_CONFIG when config.json is absent."""
        monkeypatch.setattr(voice_paste, "CONFIG_PATH", str(tmp_path / "missing.json"))
        cfg = voice_paste.load_config()
        for key, value in voice_paste.DEFAULT_CONFIG.items():
            assert cfg[key] == value

    def test_overrides_defaults_from_file(self, tmp_path, monkeypatch):
        """load_config() merges user values over defaults."""
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(
            json.dumps({"language": "fr", "auto_enter": True}), encoding="utf-8"
        )
        monkeypatch.setattr(voice_paste, "CONFIG_PATH", str(cfg_file))
        cfg = voice_paste.load_config()
        assert cfg["language"] == "fr"
        assert cfg["auto_enter"] is True
        # Other defaults intact
        assert cfg["hotkey"] == voice_paste.DEFAULT_CONFIG["hotkey"]

    def test_returns_defaults_on_invalid_json(self, tmp_path, monkeypatch):
        """load_config() falls back to defaults when config.json is corrupt."""
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text("not valid json", encoding="utf-8")
        monkeypatch.setattr(voice_paste, "CONFIG_PATH", str(cfg_file))
        cfg = voice_paste.load_config()
        assert cfg["language"] == voice_paste.DEFAULT_CONFIG["language"]

    def test_does_not_mutate_default_config(self, tmp_path, monkeypatch):
        """load_config() must not mutate the module-level DEFAULT_CONFIG dict."""
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"language": "de"}), encoding="utf-8")
        monkeypatch.setattr(voice_paste, "CONFIG_PATH", str(cfg_file))
        original_lang = voice_paste.DEFAULT_CONFIG["language"]
        voice_paste.load_config()
        assert voice_paste.DEFAULT_CONFIG["language"] == original_lang


# ── RMS calculation tests ─────────────────────────────────────────────────────


class TestGetRms:
    def test_silence_returns_zero(self):
        """Pure silence (all zeros) should yield RMS of 0."""
        data = np.zeros(1024, dtype=np.int16)
        assert voice_paste.get_rms(data) == 0.0

    def test_constant_signal(self):
        """Array of constant value n has RMS equal to n."""
        data = np.full(512, 100, dtype=np.int16)
        assert voice_paste.get_rms(data) == pytest.approx(100.0, rel=1e-5)

    def test_empty_array_returns_zero(self):
        """Empty array must not raise and must return 0."""
        data = np.array([], dtype=np.int16)
        assert voice_paste.get_rms(data) == 0.0

    def test_known_values(self):
        """Verify RMS formula: sqrt(mean(x^2))."""
        data = np.array([3, 4], dtype=np.int16)
        expected = float(np.sqrt((3**2 + 4**2) / 2))
        assert voice_paste.get_rms(data) == pytest.approx(expected, rel=1e-5)

    def test_positive_result_for_non_zero_input(self):
        """RMS must be positive for any non-zero audio data."""
        rng = np.random.default_rng(42)
        data = rng.integers(-32768, 32767, size=2048, dtype=np.int16)
        assert voice_paste.get_rms(data) > 0


# ── Audio temp-file tests ─────────────────────────────────────────────────────


class TestSaveAudioTemp:
    def test_creates_wav_file(self):
        """save_audio_temp() must create a readable WAV file."""
        raw = b"\x00\x00" * 1600  # 1,600 samples of silence
        path = voice_paste.save_audio_temp(raw)
        try:
            assert os.path.exists(path)
            assert path.endswith(".wav")
            with wave.open(path, "rb") as wf:
                assert wf.getnchannels() == voice_paste.CHANNELS
                assert wf.getsampwidth() == 2
                assert wf.getframerate() == voice_paste.SAMPLE_RATE
        finally:
            os.unlink(path)

    def test_written_bytes_match(self):
        """The frames written to the WAV must match the input bytes."""
        raw = bytes(range(256)) * 4  # 1024 bytes, 512 samples
        path = voice_paste.save_audio_temp(raw)
        try:
            with wave.open(path, "rb") as wf:
                frames = wf.readframes(wf.getnframes())
            assert frames == raw
        finally:
            os.unlink(path)

    def test_empty_audio(self):
        """save_audio_temp() must handle empty bytes without crashing."""
        path = voice_paste.save_audio_temp(b"")
        try:
            assert os.path.exists(path)
        finally:
            os.unlink(path)


# ── paste_to_active_window tests ──────────────────────────────────────────────


class TestPasteToActiveWindow:
    def setup_method(self):
        self.config = {
            **voice_paste.DEFAULT_CONFIG,
            "paste_delay": 0,
            "auto_enter": False,
        }

    def test_copies_text_to_clipboard(self):
        mock_copy = MagicMock()
        mock_hotkey = MagicMock()
        with (
            patch.object(sys.modules["pyperclip"], "copy", mock_copy),
            patch.object(sys.modules["pyautogui"], "hotkey", mock_hotkey),
        ):
            voice_paste.paste_to_active_window("hello world", self.config)
        mock_copy.assert_called_once_with("hello world")
        mock_hotkey.assert_called_once_with("ctrl", "v")

    def test_no_paste_for_empty_string(self):
        mock_copy = MagicMock()
        mock_hotkey = MagicMock()
        with (
            patch.object(sys.modules["pyperclip"], "copy", mock_copy),
            patch.object(sys.modules["pyautogui"], "hotkey", mock_hotkey),
        ):
            voice_paste.paste_to_active_window("", self.config)
        mock_copy.assert_not_called()
        mock_hotkey.assert_not_called()

    def test_no_paste_for_whitespace_only(self):
        mock_copy = MagicMock()
        with patch.object(sys.modules["pyperclip"], "copy", mock_copy):
            voice_paste.paste_to_active_window("   ", self.config)
        mock_copy.assert_not_called()

    def test_auto_enter_presses_enter(self):
        mock_press = MagicMock()
        cfg = {**self.config, "auto_enter": True}
        with (
            patch.object(sys.modules["pyperclip"], "copy", MagicMock()),
            patch.object(sys.modules["pyautogui"], "hotkey", MagicMock()),
            patch.object(sys.modules["pyautogui"], "press", mock_press),
        ):
            voice_paste.paste_to_active_window("hi", cfg)
        mock_press.assert_called_once_with("enter")

    def test_no_auto_enter_when_disabled(self):
        mock_press = MagicMock()
        with (
            patch.object(sys.modules["pyperclip"], "copy", MagicMock()),
            patch.object(sys.modules["pyautogui"], "hotkey", MagicMock()),
            patch.object(sys.modules["pyautogui"], "press", mock_press),
        ):
            voice_paste.paste_to_active_window("hi", self.config)
        mock_press.assert_not_called()


# ── Constants sanity checks ───────────────────────────────────────────────────


class TestConstants:
    def test_sample_rate(self):
        assert voice_paste.SAMPLE_RATE == 16000

    def test_channels(self):
        assert voice_paste.CHANNELS == 1

    def test_chunk(self):
        assert voice_paste.CHUNK == 1024

    def test_default_config_has_required_keys(self):
        required = {
            "language",
            "hotkey",
            "auto_enter",
            "paste_delay",
            "beep_on_ready",
            "exit_hotkey",
            "whisper_model",
            "silence_threshold",
            "silence_duration",
            "max_record_seconds",
        }
        assert required.issubset(voice_paste.DEFAULT_CONFIG.keys())
