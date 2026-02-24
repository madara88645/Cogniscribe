import json
import os
import queue
import sys
import threading
import time
import traceback
import uuid
import winsound
from typing import Any

import keyboard
import numpy as np
import pyaudio
import pyautogui
import pyperclip

from audio_processing import get_rms, preprocess_audio_bytes
from config_manager import load_config, save_config
from stt_service import STTService


SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK = 1024
FORMAT = pyaudio.paInt16


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


class BackendService:
    def __init__(self):
        self.config = load_config()
        self.stt = STTService(self.config, sample_rate=SAMPLE_RATE, channels=CHANNELS)
        self.write_lock = threading.Lock()
        self.state_lock = threading.Lock()
        self.stop_requested = threading.Event()
        self.is_listening = False
        self.listener_thread: threading.Thread | None = None
        self.running = True

    def run(self) -> None:
        self.emit("status_changed", {"status": "ready"})
        while self.running:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except Exception as exc:
                self.emit("runtime_error", {"message": f"Invalid JSON: {exc}"})
                continue
            threading.Thread(target=self._handle_request, args=(payload,), daemon=True).start()

    def _handle_request(self, payload: dict[str, Any]) -> None:
        req_id = payload.get("id")
        method = payload.get("method")
        params = payload.get("params") or {}

        try:
            if method == "ping":
                result = {"pong": True}
            elif method == "start_listening":
                result = self.start_listening()
            elif method == "stop_listening":
                result = self.stop_listening()
            elif method == "get_config":
                result = self.config
            elif method == "update_config":
                result = self.update_config(params)
            elif method == "shutdown":
                result = {"ok": True}
                self.running = False
            else:
                raise ValueError(f"Unknown method: {method}")
            self.respond(req_id, ok=True, result=result)
        except Exception as exc:
            self.respond(req_id, ok=False, error={"code": "request_failed", "message": str(exc)})

    def start_listening(self) -> dict[str, Any]:
        with self.state_lock:
            if self.is_listening:
                return {"started": False, "reason": "already_listening"}
            self.is_listening = True
            self.stop_requested.clear()
            self.listener_thread = threading.Thread(target=self._listen_worker, daemon=True)
            self.listener_thread.start()
        return {"started": True}

    def stop_listening(self) -> dict[str, Any]:
        self.stop_requested.set()
        return {"stopping": True}

    def update_config(self, patch: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(patch, dict):
            raise ValueError("patch must be an object")

        merged = _deep_merge(self.config, patch)
        save_config(merged)
        self.config = load_config()
        self.stt.reload(self.config)
        self.emit("status_changed", {"status": "ready"})
        return self.config

    def _listen_worker(self) -> None:
        trace_id = uuid.uuid4().hex[:8]
        try:
            self.emit("status_changed", {"status": "listening", "trace_id": trace_id})
            if self.config.get("beep_on_ready", True):
                self._safe_beep(850, 120)

            audio_bytes, duration = self._record_audio(self.config)
            if duration < max(0.12, float(self.config.get("min_record_seconds", 0.12))):
                self.emit("runtime_error", {"message": "Recording too short", "trace_id": trace_id})
                self.emit("status_changed", {"status": "ready", "trace_id": trace_id})
                self._safe_beep(420, 140)
                return

            self.emit("status_changed", {"status": "transcribing", "trace_id": trace_id})
            processed = preprocess_audio_bytes(
                audio_bytes=audio_bytes,
                sample_rate=SAMPLE_RATE,
                highpass_hz=float(self.config["audio"].get("highpass_hz", 80)),
                normalize_target_dbfs=float(self.config["audio"].get("normalize_target_dbfs", -20.0)),
                noise_suppression=bool(self.config["audio"].get("noise_suppression", False)),
            )

            result = self.stt.transcribe_audio_bytes(processed, self.config)
            if not result.text:
                self.emit("status_changed", {"status": "low_conf", "trace_id": trace_id})
                self.emit("runtime_error", {"message": "No speech detected", "trace_id": trace_id})
                return

            allow_low = bool(self.config["stt"].get("allow_low_confidence_paste", True))
            floor = float(self.config["stt"].get("paste_min_confidence_floor", 0.25))
            can_paste = result.accepted or (allow_low and result.confidence >= floor)

            pasted = False
            paste_error = ""
            if can_paste:
                pasted, paste_error = self._paste_text(result.text, self.config)

            if not pasted and paste_error:
                self.emit("runtime_error", {"message": paste_error, "trace_id": trace_id})

            self.emit(
                "transcript_ready",
                {
                    "text": result.text,
                    "confidence": result.confidence,
                    "accepted": result.accepted,
                    "pasted": pasted,
                    "warning": result.warning,
                    "trace_id": trace_id,
                },
            )
            self.emit(
                "metrics",
                {
                    "latency_sec": result.latency_sec,
                    "duration_audio_sec": result.duration_audio_sec,
                    "device": result.device,
                    "model": result.model,
                    "avg_logprob": result.avg_logprob,
                    "no_speech_prob": result.no_speech_prob,
                    "confidence": result.confidence,
                    "accepted": result.accepted,
                    "trace_id": trace_id,
                },
            )

            if result.accepted and pasted:
                self.emit("status_changed", {"status": "ready", "trace_id": trace_id})
                self._safe_beep(1200, 100)
            elif can_paste:
                self.emit("status_changed", {"status": "low_conf", "trace_id": trace_id})
                self._safe_beep(950, 100)
            else:
                self.emit("status_changed", {"status": "low_conf", "trace_id": trace_id})
                self._safe_beep(420, 220)
        except Exception as exc:
            self.emit(
                "runtime_error",
                {
                    "message": str(exc),
                    "trace_id": trace_id,
                    "traceback": traceback.format_exc(),
                },
            )
            self.emit("status_changed", {"status": "error", "trace_id": trace_id})
            self._safe_beep(420, 260)
        finally:
            with self.state_lock:
                self.is_listening = False
                self.stop_requested.clear()
            self.emit("status_changed", {"status": "ready", "trace_id": trace_id})

    def _record_audio(self, cfg: dict[str, Any]) -> tuple[bytes, float]:
        p = pyaudio.PyAudio()
        stream = p.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )

        frames: list[bytes] = []
        silence_counter = 0
        start_time = time.time()
        max_silence_frames = int((cfg["silence_duration"] * SAMPLE_RATE) / CHUNK)
        max_chunks = int((cfg["max_record_seconds"] * SAMPLE_RATE) / CHUNK)

        fallback_threshold = int(cfg.get("silence_threshold", 500))
        min_threshold = int(cfg["audio"].get("min_silence_threshold", 200))
        adaptive_multiplier = float(cfg["audio"].get("silence_adaptive_multiplier", 2.5))
        calibration_chunks = max(
            1,
            int(float(cfg["audio"].get("silence_calibration_seconds", 0.25)) * SAMPLE_RATE / CHUNK),
        )

        calibrated_threshold = fallback_threshold
        calibration_values: list[float] = []
        has_speech = False

        try:
            for idx in range(max_chunks):
                if self.stop_requested.is_set():
                    break

                chunk = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(chunk)
                rms = get_rms(np.frombuffer(chunk, dtype=np.int16))

                if idx < calibration_chunks and not has_speech:
                    if rms < fallback_threshold * 1.2:
                        calibration_values.append(rms)
                    if calibration_values:
                        ambient = float(np.percentile(calibration_values, 90))
                        calibrated_threshold = int(max(min_threshold, ambient * adaptive_multiplier))

                if rms > calibrated_threshold:
                    silence_counter = 0
                    has_speech = True
                else:
                    silence_counter += 1

                if has_speech and silence_counter >= max_silence_frames:
                    break
        finally:
            stream.stop_stream()
            stream.close()
            p.terminate()

        return b"".join(frames), (time.time() - start_time)

    def _paste_text(self, text: str, cfg: dict[str, Any]) -> tuple[bool, str]:
        try:
            pyperclip.copy(text)
            time.sleep(float(cfg.get("paste_delay", 0.5)))
        except Exception as exc:
            return False, f"Clipboard error: {exc}"

        try:
            pyautogui.hotkey("ctrl", "v")
            if cfg.get("auto_enter"):
                time.sleep(0.08)
                pyautogui.press("enter")
            return True, ""
        except Exception as exc:
            try:
                keyboard.send("ctrl+v")
                if cfg.get("auto_enter"):
                    keyboard.send("enter")
                return True, f"PyAutoGUI failed, keyboard fallback used: {exc}"
            except Exception as fallback_exc:
                return False, f"Paste failed: {exc}; fallback failed: {fallback_exc}"

    def _safe_beep(self, freq: int, duration: int) -> None:
        try:
            winsound.Beep(freq, duration)
        except Exception:
            pass

    def respond(self, req_id: Any, ok: bool, result: Any = None, error: Any = None) -> None:
        payload = {
            "type": "response",
            "id": req_id,
            "ok": ok,
            "result": result,
            "error": error,
        }
        self._write(payload)

    def emit(self, event: str, data: dict[str, Any]) -> None:
        payload = {
            "type": "event",
            "event": event,
            "data": data,
            "ts": time.time(),
        }
        self._write(payload)

    def _write(self, payload: dict[str, Any]) -> None:
        line = json.dumps(payload, ensure_ascii=False)
        with self.write_lock:
            sys.stdout.write(line + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    service = BackendService()
    service.run()
