"""
Voice Paste - Advanced Voice-to-Text Application
================================================
High-accuracy speech-to-text using Faster-Whisper AI model.
Records audio from microphone and pastes to active window.

Triggered by hotkey (default: Ctrl+Shift+Space).

Usage:
    python voice_paste.py          -> Continuous mode (activate on hotkey)
    python voice_paste.py --once   -> Record once and paste
"""

import json
import os
import sys
import time
import threading
import wave
import tempfile
import winsound
import numpy as np
import pyaudio

import pyautogui
import pyperclip
import keyboard
from faster_whisper import WhisperModel

# ─── Audio Constants ──────────────────────────────────────────────────────────

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK = 1024
FORMAT = pyaudio.paInt16


# ─── Configuration ────────────────────────────────────────────────────────────

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "language": "en",
    "hotkey": "ctrl+shift+space",
    "auto_enter": False,
    "paste_delay": 0.5,
    "beep_on_ready": True,
    "exit_hotkey": "ctrl+shift+q",
    "whisper_model": "base",              # tiny, base, small, medium
    "silence_threshold": 500,             # RMS value for silence detection
    "silence_duration": 1.2,              # Seconds of silence to stop recording
    "max_record_seconds": 60,             # Max recording duration
    "min_record_seconds": 0.3,            # Min recording to avoid accidental triggers
    "enable_multilingual": True,          # Auto-detect language
    "post_recording_delay": 0.5,          # Delay before processing
}


def load_config() -> dict:
    """Load config.json, use defaults if not found."""
    config = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
            config.update(user_cfg)
        except Exception as e:
            print(f"[!] Could not load config.json, using defaults: {e}")
    return config


# ─── Helper Functions ─────────────────────────────────────────────────────────

def beep_ready():
    """Beep sound indicating ready to record."""
    winsound.Beep(800, 150)


def beep_done():
    """Beep sound indicating task completed."""
    winsound.Beep(1200, 100)


def beep_error():
    """Beep sound for errors."""
    winsound.Beep(400, 300)


def get_rms(audio_data: np.ndarray) -> float:
    """Calculate RMS (Root Mean Square) of audio data."""
    if len(audio_data) == 0:
        return 0
    return np.sqrt(np.mean(audio_data.astype(float) ** 2))


def record_audio_with_silence_detection(config: dict) -> tuple[bytes, float]:
    """
    Record audio with intelligent silence detection.
    Returns: (audio_bytes, recording_duration)
    """
    p = pyaudio.PyAudio()
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=CHUNK,
    )

    frames = []
    silence_counter = 0
    recording_start = time.time()
    max_silence_frames = int(
        (config["silence_duration"] * SAMPLE_RATE) / CHUNK
    )

    try:
        print("🎤 Listening... (speak now)")
        if config["beep_on_ready"]:
            beep_ready()

        while True:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
                audio_data = np.frombuffer(data, dtype=np.int16)
                rms = get_rms(audio_data)

                # Silence detection
                if rms < config["silence_threshold"]:
                    silence_counter += 1
                else:
                    silence_counter = 0

                # Stop if silence duration exceeded
                if silence_counter > max_silence_frames and len(frames) > 10:
                    break

                # Stop if max duration exceeded
                elapsed = time.time() - recording_start
                if elapsed > config["max_record_seconds"]:
                    break

            except Exception:
                break

    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

    # Convert frames to bytes
    audio_bytes = b"".join(frames)
    duration = time.time() - recording_start

    return audio_bytes, duration


def save_audio_temp(audio_bytes: bytes) -> str:
    """Save audio bytes to temporary WAV file."""
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    with wave.open(temp_file.name, "wb") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(audio_bytes)
    temp_file.close()
    return temp_file.name


def paste_to_active_window(text: str, config: dict):
    """
    Copy text to clipboard and paste into active window.
    If auto_enter=True, also press Enter after pasting.
    """
    if not text or not text.strip():
        print("⚠️  No text to paste")
        return

    pyperclip.copy(text)
    time.sleep(config["paste_delay"])
    pyautogui.hotkey("ctrl", "v")

    if config["auto_enter"]:
        time.sleep(0.1)
        pyautogui.press("enter")


# ─── Transcription ────────────────────────────────────────────────────────────

def transcribe_audio(audio_file: str, config: dict) -> str:
    """
    Transcribe audio file using Faster-Whisper.
    Supports 100+ languages.
    """
    try:
        model_name = config["whisper_model"]
        # device can be "cpu" or "cuda" for GPU
        model = WhisperModel(model_name, device="cpu", compute_type="int8")

        segments, info = model.transcribe(
            audio_file,
            language=None if config["enable_multilingual"] else config["language"],
            beam_size=5,
        )

        text = "".join([segment.text for segment in segments]).strip()
        return text

    except Exception as e:
        print(f"❌ Transcription error: {e}")
        return ""
    finally:
        # Clean up temp file
        try:
            os.remove(audio_file)
        except:
            pass


# ─── Main Recording Function ─────────────────────────────────────────────────

def listen_and_paste(config: dict):
    """Record audio, transcribe with Whisper, and paste to active window."""
    try:
        # Record audio with silence detection
        audio_bytes, duration = record_audio_with_silence_detection(config)

        # Check minimum recording duration
        if duration < config["min_record_seconds"]:
            print(f"⏱️  Recording too short ({duration:.1f}s), ignoring")
            beep_error()
            return

        print(f"⏳ Processing... ({duration:.1f}s recorded)")

        # Save to temp file and transcribe
        audio_file = save_audio_temp(audio_bytes)
        text = transcribe_audio(audio_file, config)

        if not text:
            print("❌ Transcription failed or no speech detected")
            beep_error()
            return

        print(f"✅ Detected: {text}")

        # Wait before pasting (allow clipboard to stabilize)
        time.sleep(config["post_recording_delay"])
        paste_to_active_window(text, config)
        beep_done()

    except Exception as e:
        print(f"❌ Error: {e}")
        beep_error()


# ─── Continuous Mode (Hotkey-triggered) ──────────────────────────────────────

_last_hotkey_time = 0
_hotkey_debounce = 0.5  # Prevent triggering within 500ms


def run_continuous(config: dict):
    """
    Run in background. Listen for hotkey to trigger recording.
    Exit with exit_hotkey.
    """
    global _last_hotkey_time

    hotkey = config["hotkey"]
    exit_hotkey = config["exit_hotkey"]
    is_listening = threading.Event()

    def on_hotkey():
        global _last_hotkey_time
        current_time = time.time()

        # Debouncing: prevent rapid successive triggers
        if current_time - _last_hotkey_time < _hotkey_debounce:
            return

        _last_hotkey_time = current_time

        if is_listening.is_set():
            return  # Already recording

        is_listening.set()
        try:
            listen_and_paste(config)
        finally:
            is_listening.clear()

    print("=" * 60)
    print("  🎙️  Cogniscribe — Advanced Voice-to-Text")
    print("=" * 60)
    print(f"  Model       : Whisper ({config['whisper_model']})")
    print(f"  Language    : {config['language']}")
    print(f"  Record      : {hotkey}")
    print(f"  Exit        : {exit_hotkey}")
    print(f"  Auto-Enter  : {'Yes' if config['auto_enter'] else 'No'}")
    print(f"  Paste Delay : {config['paste_delay']}s")
    print("=" * 60)
    print("  Waiting for hotkey...\n")

    keyboard.add_hotkey(hotkey, lambda: threading.Thread(target=on_hotkey, daemon=True).start())
    keyboard.wait(exit_hotkey)

    print("\n👋 Cogniscribe closed.")


# ─── One-Shot Mode ───────────────────────────────────────────────────────────

def run_once(config: dict):
    """Record once and paste, then exit."""
    print("🎙️  Cogniscribe — One-Shot Mode")
    print("    Switch to target window in 3 seconds...\n")
    time.sleep(3)
    listen_and_paste(config)


# ─── Entry Point ──────────────────────────────────────────────────────────────

def main():
    config = load_config()

    if "--once" in sys.argv:
        run_once(config)
    else:
        run_continuous(config)


if __name__ == "__main__":
    main()
