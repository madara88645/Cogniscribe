"""
Tests for voice_paste_gui.py config and text-processing logic.

GUI toolkits (tkinter, pystray, PIL), audio hardware, and all
Windows-specific modules are mocked before the module is imported.
"""

import json
import sys
import types
from unittest.mock import MagicMock

import pytest


# ── Mock every platform/GUI dependency before importing the module ─────────────


def _make_module(name, **attrs):
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    return mod


# Already mocked by test_voice_paste.py if both run in the same process;
# setdefault keeps the first registration.
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
sys.modules.setdefault("stt_service", _make_module("stt_service", STTService=MagicMock))

# tkinter
_tk_mock = _make_module(
    "tkinter",
    Tk=MagicMock,
    Frame=MagicMock,
    Label=MagicMock,
    Canvas=MagicMock,
    BooleanVar=MagicMock,
    StringVar=MagicMock,
    Checkbutton=MagicMock,
    BOTH=MagicMock(),
    X=MagicMock(),
    LEFT=MagicMock(),
    RIGHT=MagicMock(),
    BOTTOM=MagicMock(),
)
sys.modules.setdefault("tkinter", _tk_mock)
_ttk = _make_module("tkinter.ttk", Combobox=MagicMock)
sys.modules.setdefault("tkinter.ttk", _ttk)
_tk_mock.ttk = _ttk
_messagebox = _make_module("tkinter.messagebox")
sys.modules.setdefault("tkinter.messagebox", _messagebox)
_tk_mock.messagebox = _messagebox

# pystray
_pystray = _make_module(
    "pystray",
    Icon=MagicMock,
    Menu=MagicMock,
    MenuItem=MagicMock,
)
sys.modules.setdefault("pystray", _pystray)

# PIL
_pil = _make_module("PIL", Image=MagicMock, ImageDraw=MagicMock)
sys.modules.setdefault("PIL", _pil)
sys.modules.setdefault("PIL.Image", _make_module("PIL.Image", new=MagicMock()))
sys.modules.setdefault("PIL.ImageDraw", _make_module("PIL.ImageDraw", Draw=MagicMock()))
_pil.Image = sys.modules["PIL.Image"]
_pil.ImageDraw = sys.modules["PIL.ImageDraw"]


# Import only the free functions — do NOT instantiate VoicePasteApp (needs display)
import voice_paste_gui as vpg  # noqa: E402


# ── load_config tests ──────────────────────────────────────────────────────────


class TestGuiLoadConfig:
    def test_returns_defaults_when_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(vpg, "CONFIG_PATH", str(tmp_path / "missing.json"))
        cfg = vpg.load_config()
        for key, value in vpg.DEFAULT_CONFIG.items():
            assert cfg[key] == value

    def test_merges_user_values_over_defaults(self, tmp_path, monkeypatch):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(
            json.dumps({"language": "de", "auto_enter": True}), encoding="utf-8"
        )
        monkeypatch.setattr(vpg, "CONFIG_PATH", str(cfg_file))
        cfg = vpg.load_config()
        assert cfg["language"] == "de"
        assert cfg["auto_enter"] is True

    def test_normalizes_long_locale_format(self, tmp_path, monkeypatch):
        """'tr-TR' style language codes must be normalized to 'tr'."""
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"language": "tr-TR"}), encoding="utf-8")
        monkeypatch.setattr(vpg, "CONFIG_PATH", str(cfg_file))
        cfg = vpg.load_config()
        assert cfg["language"] == "tr"

    def test_normalizes_en_US_to_en(self, tmp_path, monkeypatch):
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text(json.dumps({"language": "en-US"}), encoding="utf-8")
        monkeypatch.setattr(vpg, "CONFIG_PATH", str(cfg_file))
        cfg = vpg.load_config()
        assert cfg["language"] == "en"

    def test_silent_on_invalid_json(self, tmp_path, monkeypatch):
        """Corrupt config.json must not raise; defaults are returned."""
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text("{bad json}", encoding="utf-8")
        monkeypatch.setattr(vpg, "CONFIG_PATH", str(cfg_file))
        cfg = vpg.load_config()
        assert cfg["language"] == vpg.DEFAULT_CONFIG["language"]


# ── save_config tests ──────────────────────────────────────────────────────────


class TestGuiSaveConfig:
    def test_writes_valid_json(self, tmp_path, monkeypatch):
        cfg_file = tmp_path / "config.json"
        monkeypatch.setattr(vpg, "CONFIG_PATH", str(cfg_file))
        data = {"language": "fr", "auto_enter": False}
        vpg.save_config(data)
        saved = json.loads(cfg_file.read_text(encoding="utf-8"))
        assert saved == data

    def test_round_trip(self, tmp_path, monkeypatch):
        """save_config then load_config should reproduce the same dict."""
        cfg_file = tmp_path / "config.json"
        monkeypatch.setattr(vpg, "CONFIG_PATH", str(cfg_file))
        original = {**vpg.DEFAULT_CONFIG, "language": "es"}
        vpg.save_config(original)
        loaded = vpg.load_config()
        assert loaded["language"] == "es"

    def test_preserves_unicode(self, tmp_path, monkeypatch):
        cfg_file = tmp_path / "config.json"
        monkeypatch.setattr(vpg, "CONFIG_PATH", str(cfg_file))
        vpg.save_config({"note": "こんにちは"})
        saved = json.loads(cfg_file.read_text(encoding="utf-8"))
        assert saved["note"] == "こんにちは"


# ── _post_process_text tests ───────────────────────────────────────────────────


class TestPostProcessText:
    """
    Tests for VoicePasteApp._post_process_text() called as a plain function
    by instantiating a minimal stand-in that avoids the GUI constructor.
    """

    @pytest.fixture
    def post_process(self):
        """Return a bound reference to _post_process_text without real __init__."""
        instance = object.__new__(vpg.VoicePasteApp)
        return instance._post_process_text

    def test_non_turkish_text_is_unchanged(self, post_process):
        text = "Hello world"
        assert post_process(text, "en") == text

    def test_turkish_correction_applied(self, post_process):
        text = "bu high teknoloji"
        result = post_process(text, "tr")
        assert "hay" in result

    def test_other_language_no_correction(self, post_process):
        """Corrections must NOT be applied for non-Turkish text."""
        text = "this is high quality"
        result = post_process(text, "en")
        assert result == text

    def test_empty_string_is_safe(self, post_process):
        assert post_process("", "tr") == ""

    def test_returns_string_type(self, post_process):
        result = post_process("test", "tr")
        assert isinstance(result, str)

    def test_bugun_corrected(self, post_process):
        """'bugun' should be corrected to 'bugün' in Turkish mode."""
        result = post_process("bugun hava guzel", "tr")
        assert "bugün" in result

    def test_simdi_corrected(self, post_process):
        """'simdi' should be corrected to 'şimdi' in Turkish mode."""
        result = post_process("simdi gidelim", "tr")
        assert "şimdi" in result

    def test_multiple_spaces_collapsed(self, post_process):
        """Multiple spaces should be collapsed to a single space."""
        result = post_process("  multiple   spaces  ", "tr")
        assert result == "multiple spaces"

    def test_multiple_spaces_collapsed_non_turkish(self, post_process):
        """Space collapsing must also work for non-Turkish text."""
        result = post_process("  multiple   spaces  ", "en")
        assert result == "multiple spaces"

    def test_non_turkish_bugun_unchanged(self, post_process):
        """Phonetic corrections must NOT fire for non-Turkish languages."""
        result = post_process("bugun simdi dogru", "en")
        assert result == "bugun simdi dogru"

    def test_yarin_corrected(self, post_process):
        """'yarin' should be corrected to 'yarın' in Turkish mode."""
        result = post_process("yarin goruselim", "tr")
        assert "yarın" in result

    def test_dogru_corrected(self, post_process):
        """'dogru' should be corrected to 'doğru' in Turkish mode."""
        result = post_process("bu dogru degil", "tr")
        assert "doğru" in result


# ── LANG_MAP / DEFAULT_CONFIG sanity checks ────────────────────────────────────


class TestGuiConstants:
    def test_lang_map_has_expected_codes(self):
        for code in ("tr", "en", "de", "fr", "es"):
            assert code in vpg.LANG_MAP

    def test_default_config_has_required_keys(self):
        required = {
            "language",
            "hotkey",
            "auto_enter",
            "paste_delay",
            "beep_on_ready",
            "exit_hotkey",
            "whisper_model",
        }
        assert required.issubset(vpg.DEFAULT_CONFIG.keys())

    def test_colors_dict_present(self):
        assert isinstance(vpg.COLORS, dict)
        assert "bg" in vpg.COLORS
        assert "accent" in vpg.COLORS
