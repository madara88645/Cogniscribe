import sys
import threading
import time
import winsound

import keyboard
import numpy as np
import pyaudio
import pyautogui
import pyperclip

from audio_processing import get_rms, preprocess_audio_bytes
from config_manager import load_config
from stt_service import STTService

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK = 1024
FORMAT = pyaudio.paInt16


def beep_ready():
    winsound.Beep(800, 150)


def beep_done():
    winsound.Beep(1200, 100)


def beep_error():
    winsound.Beep(400, 300)


def paste_to_active_window(text: str, config: dict):
    if not text or not text.strip():
        print("[!] No text to paste")
        return

    pyperclip.copy(text)
    time.sleep(config["paste_delay"])
    pyautogui.hotkey("ctrl", "v")

    if config["auto_enter"]:
        time.sleep(0.1)
        pyautogui.press("enter")


def record_audio_with_silence_detection(config: dict) -> tuple[bytes, float]:
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
    max_silence_frames = int((config["silence_duration"] * SAMPLE_RATE) / CHUNK)

    fallback_threshold = int(config["silence_threshold"])
    min_threshold = int(config["audio"].get("min_silence_threshold", 200))
    adaptive_multiplier = float(config["audio"].get("silence_adaptive_multiplier", 2.5))
    calibration_chunks = max(
        1,
        int(
            float(config["audio"].get("silence_calibration_seconds", 0.25))
            * SAMPLE_RATE
            / CHUNK
        ),
    )
    calibration_values = []
    calibrated_threshold = fallback_threshold
    has_speech = False

    try:
        print("Listening... (speak now)")
        if config["beep_on_ready"]:
            beep_ready()

        chunk_idx = 0
        while True:
            try:
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
                audio_data = np.frombuffer(data, dtype=np.int16)
                rms = get_rms(audio_data)

                if chunk_idx < calibration_chunks and not has_speech:
                    if rms < fallback_threshold * 1.2:
                        calibration_values.append(rms)
                    if calibration_values:
                        ambient = float(np.percentile(calibration_values, 90))
                        calibrated_threshold = int(
                            max(min_threshold, ambient * adaptive_multiplier)
                        )
                chunk_idx += 1

                if rms < calibrated_threshold:
                    silence_counter += 1
                else:
                    silence_counter = 0
                    has_speech = True

                if silence_counter > max_silence_frames and len(frames) > 10:
                    break

                elapsed = time.time() - recording_start
                if elapsed > config["max_record_seconds"]:
                    break

            except Exception:
                break

    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()

    duration = time.time() - recording_start
    return b"".join(frames), duration


_last_hotkey_time = 0
_hotkey_debounce = 0.5


def listen_and_paste(config: dict, stt: STTService):
    try:
        audio_bytes, duration = record_audio_with_silence_detection(config)

        if duration < config["min_record_seconds"]:
            print(f"Recording too short ({duration:.1f}s), ignoring")
            beep_error()
            return

        print(f"Processing... ({duration:.1f}s recorded)")

        processed_audio = preprocess_audio_bytes(
            audio_bytes=audio_bytes,
            sample_rate=SAMPLE_RATE,
            highpass_hz=float(config["audio"]["highpass_hz"]),
            normalize_target_dbfs=float(config["audio"]["normalize_target_dbfs"]),
            noise_suppression=bool(config["audio"]["noise_suppression"]),
        )

        result = stt.transcribe_audio_bytes(processed_audio, config)

        if not result.text:
            print("Transcription failed or no speech detected")
            beep_error()
            return

        allow_low_conf = bool(config["stt"].get("allow_low_confidence_paste", True))
        low_conf_floor = float(config["stt"].get("paste_min_confidence_floor", 0.25))
        if not result.accepted and (
            not allow_low_conf or result.confidence < low_conf_floor
        ):
            print(f"Low confidence ({result.confidence:.2f}). {result.warning}")
            beep_error()
            return

        if result.accepted:
            print(f"Detected: {result.text}")
        else:
            print(f"Detected (low confidence): {result.text}")
        print(
            f"[STT] latency={result.latency_sec:.2f}s model={result.model} "
            f"device={result.device} confidence={result.confidence:.2f}"
        )

        time.sleep(config["post_recording_delay"])
        paste_to_active_window(result.text, config)
        beep_done()

    except Exception as exc:
        print(f"Error: {exc}")
        beep_error()


def run_continuous(config: dict, stt: STTService):
    global _last_hotkey_time

    hotkey = config["hotkey"]
    exit_hotkey = config["exit_hotkey"]
    is_listening = threading.Event()

    def on_hotkey():
        global _last_hotkey_time
        current_time = time.time()

        if current_time - _last_hotkey_time < _hotkey_debounce:
            return

        _last_hotkey_time = current_time

        if is_listening.is_set():
            return

        is_listening.set()
        try:
            listen_and_paste(config, stt)
        finally:
            is_listening.clear()

    print("=" * 60)
    print("Voice Paste")
    print("=" * 60)
    print(f"Model CPU   : {config['stt']['model_cpu']}")
    print(f"Model GPU   : {config['stt']['model_gpu']}")
    print(f"Device mode : {config['stt']['device']}")
    print(f"Lang mode   : {config['stt']['language_mode']}")
    print(f"Record      : {hotkey}")
    print(f"Exit        : {exit_hotkey}")
    print("=" * 60)
    print("Waiting for hotkey...\n")

    keyboard.add_hotkey(
        hotkey, lambda: threading.Thread(target=on_hotkey, daemon=True).start()
    )
    keyboard.wait(exit_hotkey)
    print("Voice Paste closed.")


def run_once(config: dict, stt: STTService):
    print("Voice Paste -- One-Shot Mode")
    print("Switch to target window in 3 seconds...\n")
    time.sleep(3)
    listen_and_paste(config, stt)


def main():
    config = load_config()
    stt = STTService(config=config, sample_rate=SAMPLE_RATE, channels=CHANNELS)

    if "--once" in sys.argv:
        run_once(config, stt)
    else:
        run_continuous(config, stt)


if __name__ == "__main__":
    main()
