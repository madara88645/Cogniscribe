import sys
import threading
import time
import winsound
import traceback
import os

import keyboard
import numpy as np
import pyaudio
import pyautogui
import pyperclip
import tkinter as tk
from tkinter import ttk

from audio_processing import get_rms, preprocess_audio_bytes
from config_manager import load_config, save_config
from stt_service import STTService

import pystray
from PIL import Image, ImageDraw

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK = 1024
FORMAT = pyaudio.paInt16

THEME = {
    "bg": "#f6f1e8",
    "panel": "#ffffff",
    "panel_2": "#efe7da",
    "text": "#2f2a24",
    "muted": "#6a6258",
    "accent": "#9a6b2f",
    "accent_hover": "#7f5522",
    "danger": "#b04a3f",
    "ok": "#2f7a4b",
    "warn": "#b67d2d",
    "border": "#dfd2bf",
}


class VoicePasteApp:
    def __init__(self):
        self.config = load_config()
        self.is_listening = False
        self.stop_requested = threading.Event()
        self.model_loading = False
        self.model_ready = False
        self.last_toggle_time = 0.0
        self.toggle_debounce_sec = 0.35
        self.stt = None
        self.pa = pyaudio.PyAudio()

        self.root = tk.Tk()
        self.root.title("Voice Paste Studio")
        self.root.geometry("390x560")
        self.root.resizable(False, False)
        self.root.configure(bg=THEME["bg"])
        self.root.attributes("-topmost", True)
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

        self.tray_icon = None

        self._setup_styles()
        self._build_ui()
        self._setup_hotkey()
        self._setup_tray()
        self._position_bottom_right()
        self._init_stt_async()

    def _setup_styles(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "Studio.TCombobox",
            fieldbackground="#ffffff",
            background="#ffffff",
            foreground=THEME["text"],
            bordercolor=THEME["border"],
            lightcolor=THEME["border"],
            darkcolor=THEME["border"],
            relief="flat",
            padding=4,
        )

    def _build_ui(self):
        top = tk.Frame(
            self.root,
            bg=THEME["panel"],
            highlightbackground=THEME["border"],
            highlightthickness=1,
        )
        top.pack(fill="x", padx=16, pady=(16, 10))

        title_row = tk.Frame(top, bg=THEME["panel"])
        title_row.pack(fill="x", padx=14, pady=(12, 4))
        tk.Label(
            title_row,
            text="Voice Paste Studio",
            bg=THEME["panel"],
            fg=THEME["text"],
            font=("Georgia", 15, "bold"),
        ).pack(side="left")

        self.pin_var = tk.BooleanVar(value=True)
        self.pin_btn = tk.Label(
            title_row,
            text="PIN",
            bg=THEME["panel_2"],
            fg=THEME["text"],
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=3,
            cursor="hand2",
        )
        self.pin_btn.pack(side="right")
        self.pin_btn.bind("<Button-1>", self.toggle_pin)

        subtitle = tk.Label(
            top,
            text="TR + EN dictation with local Whisper",
            bg=THEME["panel"],
            fg=THEME["muted"],
            font=("Segoe UI", 9),
        )
        subtitle.pack(anchor="w", padx=14, pady=(0, 12))

        status_box = tk.Frame(
            self.root,
            bg=THEME["panel"],
            highlightbackground=THEME["border"],
            highlightthickness=1,
        )
        status_box.pack(fill="x", padx=16, pady=(0, 10))

        self.status_dot = tk.Canvas(
            status_box, width=10, height=10, bg=THEME["panel"], highlightthickness=0
        )
        self.status_dot.pack(side="left", padx=(14, 6), pady=12)
        self.status_dot.create_oval(1, 1, 9, 9, fill=THEME["warn"], outline="")

        self.status_label = tk.Label(
            status_box,
            text="Model loading...",
            bg=THEME["panel"],
            fg=THEME["warn"],
            font=("Segoe UI", 9, "bold"),
        )
        self.status_label.pack(side="left", pady=12)

        mic_wrap = tk.Frame(self.root, bg=THEME["bg"])
        mic_wrap.pack(pady=(10, 8))

        self.mic_btn = tk.Canvas(
            mic_wrap,
            width=108,
            height=108,
            bg=THEME["bg"],
            highlightthickness=0,
            cursor="hand2",
        )
        self.mic_btn.pack()
        self._draw_mic_button(THEME["accent"], text="WAIT")
        self.mic_btn.bind("<Button-1>", lambda e: self.toggle_listening())

        hotkey = self.config["hotkey"].replace("+", " + ").upper()
        tk.Label(
            self.root,
            text=f"Shortcut: {hotkey}",
            bg=THEME["bg"],
            fg=THEME["muted"],
            font=("Segoe UI", 8),
        ).pack()

        controls = tk.Frame(
            self.root,
            bg=THEME["panel"],
            highlightbackground=THEME["border"],
            highlightthickness=1,
        )
        controls.pack(fill="x", padx=16, pady=(10, 10))

        self._combo_row(
            controls,
            0,
            "Model",
            "model_var",
            ["tiny", "base", "small", "medium", "large-v3"],
            self.config["stt"].get("model_cpu", "small"),
            self.on_model_change,
        )
        self._combo_row(
            controls,
            1,
            "Profile",
            "profile_var",
            ["fast", "balanced", "quality"],
            self.config["stt"].get("quality_profile", "balanced"),
            self.on_profile_change,
        )
        self._combo_row(
            controls,
            2,
            "Language Mode",
            "lang_mode_var",
            ["tr_en_mixed", "multilingual_auto"],
            self.config["stt"].get("language_mode", "tr_en_mixed"),
            self.on_language_mode_change,
        )

        self.auto_enter_var = tk.BooleanVar(value=self.config["auto_enter"])
        ae = tk.Checkbutton(
            controls,
            text="Auto Enter after paste",
            variable=self.auto_enter_var,
            bg=THEME["panel"],
            fg=THEME["text"],
            selectcolor=THEME["panel"],
            activebackground=THEME["panel"],
            activeforeground=THEME["text"],
            command=self.on_auto_enter_change,
            font=("Segoe UI", 9),
        )
        ae.grid(row=3, column=0, columnspan=2, sticky="w", padx=14, pady=(2, 10))

        out = tk.Frame(
            self.root,
            bg=THEME["panel"],
            highlightbackground=THEME["border"],
            highlightthickness=1,
        )
        out.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        tk.Label(
            out,
            text="Last transcript",
            bg=THEME["panel"],
            fg=THEME["muted"],
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="w", padx=14, pady=(10, 4))
        self.result_label = tk.Label(
            out,
            text="-",
            bg=THEME["panel"],
            fg=THEME["text"],
            font=("Segoe UI", 10),
            justify="left",
            anchor="w",
            wraplength=340,
        )
        self.result_label.pack(fill="x", padx=14, pady=(0, 10))

        tk.Label(
            out,
            text="Session metrics",
            bg=THEME["panel"],
            fg=THEME["muted"],
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor="w", padx=14, pady=(2, 2))
        self.metrics_label = tk.Label(
            out,
            text="-",
            bg=THEME["panel"],
            fg=THEME["muted"],
            font=("Consolas", 8),
            justify="left",
            anchor="w",
        )
        self.metrics_label.pack(fill="x", padx=14, pady=(0, 12))

        exit_key = self.config["exit_hotkey"].replace("+", " + ").upper()
        tk.Label(
            self.root,
            text=f"Exit: {exit_key}",
            bg=THEME["bg"],
            fg=THEME["muted"],
            font=("Segoe UI", 8),
        ).pack(pady=(0, 8))

    def _combo_row(self, parent, row, label, var_name, values, default_value, callback):
        tk.Label(
            parent,
            text=label,
            bg=THEME["panel"],
            fg=THEME["muted"],
            font=("Segoe UI", 8, "bold"),
        ).grid(row=row, column=0, sticky="w", padx=(14, 8), pady=7)
        var = tk.StringVar(value=default_value)
        combo = ttk.Combobox(
            parent,
            textvariable=var,
            values=values,
            state="readonly",
            width=18,
            style="Studio.TCombobox",
        )
        combo.grid(row=row, column=1, sticky="w", padx=(0, 14), pady=7)
        combo.bind("<<ComboboxSelected>>", callback)
        setattr(self, var_name, var)

    def _init_stt_async(self):
        self.model_loading = True
        threading.Thread(target=self._init_stt_worker, daemon=True).start()

    def _init_stt_worker(self):
        try:
            self.stt = STTService(
                self.config, sample_rate=SAMPLE_RATE, channels=CHANNELS
            )
            self.model_ready = True
            self.root.after(0, lambda: self._set_status("Ready", THEME["ok"]))
            self.root.after(
                0, lambda: self._draw_mic_button(THEME["accent"], text="MIC")
            )
        except Exception as exc:
            error_message = str(exc)
            self.model_ready = False
            self.root.after(0, lambda: self._set_status("Model error", THEME["danger"]))
            self.root.after(
                0,
                lambda: self.result_label.config(
                    text=f"Model load failed: {error_message}"
                ),
            )
            self.root.after(
                0, lambda: self._draw_mic_button(THEME["danger"], text="ERR")
            )
        finally:
            self.model_loading = False

    def _record_audio(self) -> bytes:
        cfg = self.config
        stream = self.pa.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )

        frames = []
        silence_counter = 0
        max_silence_frames = int((cfg["silence_duration"] * SAMPLE_RATE) / CHUNK)
        max_chunks = int((cfg["max_record_seconds"] * SAMPLE_RATE) / CHUNK)
        fallback_threshold = int(cfg["silence_threshold"])
        min_threshold = int(cfg["audio"].get("min_silence_threshold", 200))
        adaptive_multiplier = float(
            cfg["audio"].get("silence_adaptive_multiplier", 2.5)
        )
        calibration_chunks = max(
            1,
            int(
                float(cfg["audio"].get("silence_calibration_seconds", 0.25))
                * SAMPLE_RATE
                / CHUNK
            ),
        )
        calibration_values = []
        calibrated_threshold = fallback_threshold

        has_speech = False
        try:
            for idx in range(max_chunks):
                if self.stop_requested.is_set():
                    break
                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)
                rms = get_rms(np.frombuffer(data, dtype=np.int16))

                # Calibrate threshold from low-energy ambient chunks only.
                if idx < calibration_chunks and not has_speech:
                    if rms < fallback_threshold * 1.2:
                        calibration_values.append(rms)
                    if calibration_values:
                        ambient = float(np.percentile(calibration_values, 90))
                        calibrated_threshold = int(
                            max(min_threshold, ambient * adaptive_multiplier)
                        )

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

        return b"".join(frames)

    def toggle_listening(self):
        now = time.time()
        if now - self.last_toggle_time < self.toggle_debounce_sec:
            return
        self.last_toggle_time = now

        if self.model_loading or not self.model_ready or self.stt is None:
            self._set_status("Model still loading", THEME["warn"])
            return

        if self.is_listening:
            self.stop_requested.set()
            self._set_status("Stopping...", THEME["warn"])
            return

        self.stop_requested.clear()
        self.is_listening = True
        self._set_status("Listening...", THEME["danger"])
        self.result_label.config(text="Speak now...")
        self._draw_mic_button(THEME["danger"], text="STOP")
        threading.Thread(target=self._listen_worker, daemon=True).start()

    def _listen_worker(self):
        cfg = self.config
        try:
            if cfg["beep_on_ready"]:
                winsound.Beep(850, 130)

            audio_bytes = self._record_audio()
            duration = len(audio_bytes) / float(SAMPLE_RATE * CHANNELS * 2)
            if duration < max(0.12, float(cfg["min_record_seconds"])):
                self.root.after(0, lambda: self._set_status("Too short", THEME["warn"]))
                self.root.after(
                    0, lambda: self.result_label.config(text="Recording too short")
                )
                winsound.Beep(420, 180)
                return

            self.root.after(
                0, lambda: self._set_status("Transcribing...", THEME["warn"])
            )

            processed = preprocess_audio_bytes(
                audio_bytes=audio_bytes,
                sample_rate=SAMPLE_RATE,
                highpass_hz=float(cfg["audio"]["highpass_hz"]),
                normalize_target_dbfs=float(cfg["audio"]["normalize_target_dbfs"]),
                noise_suppression=bool(cfg["audio"]["noise_suppression"]),
            )

            result = self.stt.transcribe_audio_bytes(processed, cfg)

            if not result.text:
                self.root.after(0, lambda: self._set_status("No speech", THEME["warn"]))
                self.root.after(
                    0, lambda: self.result_label.config(text="No speech detected")
                )
                winsound.Beep(420, 230)
                return

            low_conf_allowed = bool(cfg["stt"].get("allow_low_confidence_paste", True))
            low_conf_floor = float(cfg["stt"].get("paste_min_confidence_floor", 0.25))
            if not result.accepted and (
                not low_conf_allowed or result.confidence < low_conf_floor
            ):
                self.root.after(
                    0, lambda: self._set_status("Low confidence", THEME["warn"])
                )
                self.root.after(
                    0, lambda: self.result_label.config(text=result.warning)
                )
                self.root.after(
                    0,
                    lambda: self.metrics_label.config(
                        text=(
                            f"conf={result.confidence:.2f}"
                            f" logprob={result.avg_logprob:.2f}"
                        )
                    ),
                )
                winsound.Beep(420, 230)
                return

            text = self._post_process_text(result.text)
            ok, paste_message = self._paste_text(text, cfg)
            if not ok:
                self.root.after(
                    0, lambda: self._set_status("Paste warning", THEME["warn"])
                )
                self.root.after(
                    0, lambda: self.metrics_label.config(text=paste_message)
                )

            winsound.Beep(1200, 100)
            display = text if len(text) <= 130 else text[:127] + "..."
            self.root.after(0, lambda: self.result_label.config(text=display))
            if ok:
                if result.accepted:
                    self.root.after(0, lambda: self._set_status("Ready", THEME["ok"]))
                else:
                    self.root.after(
                        0, lambda: self._set_status("Pasted (low conf)", THEME["warn"])
                    )
                self.root.after(
                    0,
                    lambda: self.metrics_label.config(
                        text=(
                            f"{result.device}/{result.model}"
                            f"  latency={result.latency_sec:.2f}s"
                            f"  conf={result.confidence:.2f}"
                        )
                    ),
                )

        except Exception as exc:
            error_message = str(exc)
            self._log_runtime_error(exc)
            self.root.after(0, lambda: self._set_status("Error", THEME["danger"]))
            self.root.after(
                0, lambda: self.result_label.config(text=f"Error: {error_message}")
            )
            winsound.Beep(420, 260)
        finally:
            self.is_listening = False
            self.root.after(
                0,
                lambda: self._draw_mic_button(
                    THEME["accent"], text="MIC" if self.model_ready else "WAIT"
                ),
            )

    def _paste_text(self, text: str, cfg: dict) -> tuple[bool, str]:
        try:
            pyperclip.copy(text)
            time.sleep(cfg["paste_delay"])
        except Exception as exc:
            return False, f"Clipboard error: {exc}"

        try:
            pyautogui.hotkey("ctrl", "v")
            if cfg["auto_enter"]:
                time.sleep(0.08)
                pyautogui.press("enter")
            return True, ""
        except Exception as exc:
            try:
                keyboard.send("ctrl+v")
                if cfg["auto_enter"]:
                    keyboard.send("enter")
                return True, f"PyAutoGUI failed, keyboard fallback used: {exc}"
            except Exception as fallback_exc:
                return False, f"Paste failed: {exc}; fallback failed: {fallback_exc}"

    def _log_runtime_error(self, exc: Exception) -> None:
        try:
            logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
            os.makedirs(logs_dir, exist_ok=True)
            path = os.path.join(logs_dir, "gui_errors.log")
            with open(path, "a", encoding="utf-8") as f:
                f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] {exc}\n")
                f.write(traceback.format_exc())
        except Exception:
            pass

    def _post_process_text(self, text: str) -> str:
        return " ".join(text.split()).strip()

    def _set_status(self, text, color):
        self.status_dot.delete("all")
        self.status_dot.create_oval(1, 1, 9, 9, fill=color, outline="")
        self.status_label.config(text=text, fg=color)

    def _draw_mic_button(self, color, text="MIC"):
        c = self.mic_btn
        c.delete("all")
        c.create_oval(4, 4, 104, 104, fill=color, outline="")
        c.create_text(54, 54, text=text, fill="#ffffff", font=("Segoe UI", 11, "bold"))

    def on_model_change(self, event=None):
        self.config["stt"]["model_cpu"] = self.model_var.get()
        save_config(self.config)
        self.model_ready = False
        self._set_status("Reloading model...", THEME["warn"])
        self._draw_mic_button(THEME["warn"], text="WAIT")
        self._init_stt_async()

    def on_profile_change(self, event=None):
        self.config["stt"]["quality_profile"] = self.profile_var.get()
        save_config(self.config)

    def on_language_mode_change(self, event=None):
        self.config["stt"]["language_mode"] = self.lang_mode_var.get()
        save_config(self.config)

    def on_auto_enter_change(self):
        self.config["auto_enter"] = self.auto_enter_var.get()
        save_config(self.config)

    def toggle_pin(self, event=None):
        val = not self.pin_var.get()
        self.pin_var.set(val)
        self.root.attributes("-topmost", val)
        self.pin_btn.config(text="PIN" if val else "FREE")

    def _position_bottom_right(self):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        self.root.geometry(f"+{sw - w - 20}+{sh - h - 60}")

    def _create_tray_image(self):
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        draw.ellipse([2, 2, size - 2, size - 2], fill=THEME["accent"])
        draw.rectangle([28, 15, 36, 44], fill="white")
        draw.rectangle([24, 44, 40, 50], fill="white")
        return img

    def _setup_tray(self):
        image = self._create_tray_image()
        menu = pystray.Menu(
            pystray.MenuItem("Show", self._tray_show, default=True),
            pystray.MenuItem("Listen", self._tray_listen),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Exit", self._tray_quit),
        )
        self.tray_icon = pystray.Icon("VoicePaste", image, "Voice Paste Studio", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def _setup_hotkey(self):
        keyboard.add_hotkey(
            self.config["hotkey"], lambda: self.root.after(0, self.toggle_listening)
        )
        keyboard.add_hotkey(
            self.config["exit_hotkey"], lambda: self.root.after(0, self.on_close)
        )

    def minimize_to_tray(self):
        self.root.withdraw()

    def _tray_show(self, icon=None, item=None):
        self.root.after(0, self._restore_window)

    def _restore_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _tray_listen(self, icon=None, item=None):
        self.root.after(0, self.toggle_listening)

    def _tray_quit(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self.on_close)

    def on_close(self):
        keyboard.unhook_all()
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        try:
            self.pa.terminate()
        except Exception:
            pass
        self.root.destroy()
        sys.exit(0)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = VoicePasteApp()
    app.run()
