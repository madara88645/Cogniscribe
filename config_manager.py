import copy
import json
import os
import re
from typing import Any


CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")


DEFAULT_CONFIG = {
    "language": "tr",
    "hotkey": "ctrl+shift+space",
    "auto_enter": False,
    "paste_delay": 0.5,
    "beep_on_ready": True,
    "exit_hotkey": "ctrl+shift+q",
    "silence_threshold": 500,
    "silence_duration": 1.2,
    "max_record_seconds": 60,
    "min_record_seconds": 0.12,
    "post_recording_delay": 0.5,
    "stt": {
        "backend": "faster_whisper_local",
        "model_cpu": "small",
        "model_gpu": "large-v3",
        "device": "auto",
        "compute_type_cpu": "int8",
        "compute_type_gpu": "float16",
        "language_mode": "tr_en_mixed",
        "primary_language": "tr",
        "quality_profile": "balanced",
        "beam_size": 3,
        "best_of": 3,
        "vad_filter": True,
        "min_confidence_for_accept": 0.35,
        "allow_low_confidence_paste": True,
        "paste_min_confidence_floor": 0.25,
        "retry_on_low_confidence": True,
        "use_legacy_decode_values": False,
        "term_hints": [
            "proje",
            "projenin",
            "plani",
            "planini",
            "implementasyon",
            "entegrasyon",
            "api",
            "endpoint",
            "deployment",
            "microservice",
            "yapmamiz",
            "gerekiyor",
        ],
    },
    "audio": {
        "noise_suppression": False,
        "highpass_hz": 80,
        "normalize_target_dbfs": -20.0,
        "silence_calibration_seconds": 0.25,
        "silence_adaptive_multiplier": 2.5,
        "min_silence_threshold": 200,
    },
    "telemetry": {
        "enabled": True,
        "log_path": "logs/transcribe_metrics.jsonl",
    },
    "ui": {
        "window": {
            "width": 420,
            "height": 620,
            "always_on_top": True,
        },
        "theme": {
            "mode": "light",
            "accent": "#9a6b2f",
        },
        "density": "compact",
        "motion": "subtle",
    },
}


QUALITY_PROFILES = {
    "fast": {"beam_size": 1, "best_of": 1, "temperature": [0.0], "vad_filter": True},
    "balanced": {
        "beam_size": 3,
        "best_of": 3,
        "temperature": [0.0, 0.2],
        "vad_filter": True,
    },
    "quality": {
        "beam_size": 5,
        "best_of": 5,
        "temperature": [0.0, 0.2, 0.4],
        "vad_filter": True,
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _coerce_language(language: str) -> str:
    if not isinstance(language, str):
        return "tr"
    if "-" in language:
        return language.split("-")[0].lower()
    return language.lower()


def _migrate_legacy(config: dict[str, Any]) -> dict[str, Any]:
    stt = config.setdefault("stt", {})
    audio = config.setdefault("audio", {})
    telemetry = config.setdefault("telemetry", {})
    ui = config.setdefault("ui", {})

    # Legacy keys from old config layout.
    if "whisper_model" in config and "model_cpu" not in stt:
        stt["model_cpu"] = config["whisper_model"]
    if "whisper_model" in config and "model_gpu" not in stt:
        stt["model_gpu"] = "large-v3" if config["whisper_model"] in ("small", "medium", "large-v3") else "small"
    if "language" in config and "primary_language" not in stt:
        stt["primary_language"] = _coerce_language(config["language"])
    if "enable_multilingual" in config and "language_mode" not in stt:
        stt["language_mode"] = "multilingual_auto" if config["enable_multilingual"] else "tr_en_mixed"

    stt.setdefault("backend", "faster_whisper_local")
    stt.setdefault("device", "auto")
    stt.setdefault("compute_type_cpu", "int8")
    stt.setdefault("compute_type_gpu", "float16")
    stt.setdefault("quality_profile", "balanced")
    stt.setdefault("beam_size", 3)
    stt.setdefault("best_of", 3)
    stt.setdefault("vad_filter", True)
    stt.setdefault("min_confidence_for_accept", 0.35)
    stt.setdefault("allow_low_confidence_paste", True)
    stt.setdefault("paste_min_confidence_floor", 0.25)
    stt.setdefault("retry_on_low_confidence", True)
    stt.setdefault("use_legacy_decode_values", False)
    stt.setdefault(
        "term_hints",
        [
            "proje",
            "projenin",
            "plani",
            "planini",
            "implementasyon",
            "entegrasyon",
            "api",
            "endpoint",
            "deployment",
            "microservice",
            "yapmamiz",
            "gerekiyor",
        ],
    )
    stt["term_hints"] = _sanitize_hints(stt.get("term_hints", []))
    stt["primary_language"] = _coerce_language(stt.get("primary_language", config.get("language", "tr")))

    audio.setdefault("noise_suppression", False)
    audio.setdefault("highpass_hz", 80)
    audio.setdefault("normalize_target_dbfs", -20.0)
    audio.setdefault("silence_calibration_seconds", 0.25)
    audio.setdefault("silence_adaptive_multiplier", 2.5)
    audio.setdefault("min_silence_threshold", 200)

    telemetry.setdefault("enabled", True)
    telemetry.setdefault("log_path", "logs/transcribe_metrics.jsonl")

    ui_window = ui.setdefault("window", {})
    ui_theme = ui.setdefault("theme", {})
    ui_window.setdefault("width", 420)
    ui_window.setdefault("height", 620)
    ui_window.setdefault("always_on_top", True)
    ui_theme.setdefault("mode", "light")
    ui_theme.setdefault("accent", "#9a6b2f")
    ui.setdefault("density", "compact")
    ui.setdefault("motion", "subtle")

    config["language"] = _coerce_language(config.get("language", stt["primary_language"]))
    return config


def load_config() -> dict[str, Any]:
    config = copy.deepcopy(DEFAULT_CONFIG)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
            config = _deep_merge(config, user_cfg)
        except Exception as exc:
            print(f"[!] Could not load config.json, using defaults: {exc}")

    config = _migrate_legacy(config)

    # Apply environment variable overrides. Use prefix VOICE_PASTE_ and double-underscore
    # to denote nested keys, e.g. VOICE_PASTE_STT__BACKEND=faster_whisper_local
    def _set_in_path(cfg: dict[str, Any], path: list[str], value: Any) -> None:
        cur = cfg
        for p in path[:-1]:
            if p not in cur or not isinstance(cur[p], dict):
                cur[p] = {}
            cur = cur[p]
        cur[path[-1]] = value

    def _coerce_env_value(val: str) -> Any:
        v = val.strip()
        if not v:
            return ""
        low = v.lower()
        if low in ("true", "false"):
            return low == "true"
        # try integer
        try:
            return int(v)
        except Exception:
            pass
        # try float
        try:
            return float(v)
        except Exception:
            pass
        # try json (list/dict)
        try:
            return json.loads(v)
        except Exception:
            pass
        # comma-separated list
        if "," in v:
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    prefix = "VOICE_PASTE_"
    for name, val in os.environ.items():
        if not name.startswith(prefix):
            continue
        key = name[len(prefix) :].lower()
        # support double underscore for nested keys
        parts = [p for p in key.split("__") if p]
        if not parts:
            continue
        _set_in_path(config, parts, _coerce_env_value(val))

    return _deep_merge(DEFAULT_CONFIG, config)


def save_config(config: dict[str, Any]) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


def get_profile_decode_options(config: dict[str, Any]) -> dict[str, Any]:
    stt = config["stt"]
    profile_name = str(stt.get("quality_profile", "balanced")).lower()
    profile = QUALITY_PROFILES.get(profile_name, QUALITY_PROFILES["balanced"])
    if bool(stt.get("use_legacy_decode_values", False)):
        return {
            "beam_size": int(stt.get("beam_size", profile["beam_size"])),
            "best_of": int(stt.get("best_of", profile["best_of"])),
            "temperature": profile["temperature"],
            "vad_filter": bool(stt.get("vad_filter", profile["vad_filter"])),
        }
    return {
        "beam_size": int(profile["beam_size"]),
        "best_of": int(profile["best_of"]),
        "temperature": profile["temperature"],
        "vad_filter": bool(profile["vad_filter"]),
    }


def _sanitize_hints(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    out = []
    for v in values:
        if not isinstance(v, str):
            continue
        cleaned = re.sub(r"\s+", " ", v.strip().lower())
        if cleaned:
            out.append(cleaned)
    return out[:32]
