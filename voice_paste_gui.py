"""
Voice Paste GUI — Whisper destekli sesli yapıştırma aracı.
Mikrofondan sesi alır, faster-whisper ile metne çevirir, aktif pencereye yapıştırır.
"""

import json
import os
import sys
import time
import threading
import wave
import tempfile
import io
import winsound

import numpy as np
import pyaudio
import pyautogui
import pyperclip
import keyboard
from faster_whisper import WhisperModel

import tkinter as tk
from tkinter import ttk, messagebox

import pystray
from PIL import Image, ImageDraw


# ─── Ses Sabitleri ─────────────────────────────────────────────────────────────

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK = 1024
FORMAT = pyaudio.paInt16
SILENCE_THRESHOLD = 500       # Sessizlik eşiği (RMS)
SILENCE_DURATION = 2.0        # Bu kadar saniye sessizse kaydı bitir
MAX_RECORD_SECONDS = 60       # Maksimum kayıt süresi
MIN_RECORD_SECONDS = 0.5      # Minimum kayıt süresi (çok kısa kayıtları atla)


# ─── Konfigürasyon ────────────────────────────────────────────────────────────

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "language": "tr",
    "hotkey": "ctrl+shift+space",
    "auto_enter": False,
    "paste_delay": 0.3,
    "beep_on_ready": True,
    "exit_hotkey": "ctrl+shift+q",
    "whisper_model": "base",
    "silence_threshold": 500,
    "silence_duration": 2.0,
    "max_record_seconds": 60,
}

# Whisper dil kodları (kısa) → gösterim
LANG_MAP = {
    "tr": "Türkçe",
    "en": "English",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
    "ar": "العربية",
    "ja": "日本語",
    "zh": "中文",
}


def load_config() -> dict:
    config = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
            config.update(user_cfg)
        except Exception:
            pass
    # Eski "tr-TR" formatını "tr" ye dönüştür
    lang = config["language"]
    if "-" in lang:
        config["language"] = lang.split("-")[0].lower()
    return config


def save_config(config: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


# ─── Renkler & Stil ───────────────────────────────────────────────────────────

COLORS = {
    "bg": "#1e1e2e",
    "surface": "#2a2a3c",
    "accent": "#7c3aed",
    "accent_hover": "#6d28d9",
    "recording": "#ef4444",
    "recording_hover": "#dc2626",
    "success": "#22c55e",
    "warning": "#f59e0b",
    "text": "#e2e8f0",
    "text_dim": "#94a3b8",
    "border": "#3a3a5c",
}


# ─── Ana Uygulama ─────────────────────────────────────────────────────────────

class VoicePasteApp:
    def __init__(self):
        self.config = load_config()
        self.is_listening = False
        self.stop_requested = threading.Event()  # Kaydi manuel durdurma flagi
        self.whisper_model = None
        self.model_loading = False
        self.pa = pyaudio.PyAudio()

        # ── Ana Pencere ──
        self.root = tk.Tk()
        self.root.title("Voice Paste")
        self.root.geometry("290x380")
        self.root.resizable(False, False)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=COLORS["bg"])
        self.root.overrideredirect(False)

        # İkon ayarla (varsa)
        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        # X'e basınca tray'e küçült, tam kapatma sağ tık > Çıkış
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

        self.tray_icon = None

        self._build_ui()
        self._setup_hotkey()
        self._setup_tray()
        self._position_bottom_right()

        # Model'i arka planda yükle
        self._load_model_async()

    # ── Whisper Model ──

    def _load_model_async(self):
        """Whisper modelini arka planda yükle (ilk seferde indirir)."""
        self.model_loading = True
        self.root.after(0, lambda: self._set_status("Model yükleniyor...", COLORS["warning"]))
        thread = threading.Thread(target=self._load_model_worker, daemon=True)
        thread.start()

    def _load_model_worker(self):
        try:
            model_name = self.config.get("whisper_model", "base")
            # CPU kullan (CUDA kütüphaneleri yoksa)
            self.whisper_model = WhisperModel(
                model_name, device="cpu", compute_type="int8"
            )
            self.model_loading = False
            self.root.after(0, lambda: self._set_status("Hazır", COLORS["success"]))
        except Exception as e:
            self.model_loading = False
            self.root.after(0, lambda: self._set_status(f"Model hatası!", COLORS["recording"]))
            self.root.after(0, lambda: self.result_label.config(text=f"❌ {e}"))

    # ── Ses Kayıt ──

    def _record_audio(self) -> bytes:
        """
        Mikrofondan ses kaydeder. Sessizlik algılandığında veya max süre dolunca durur.
        WAV formatında bytes döndürür.
        """
        config = self.config
        silence_threshold = config.get("silence_threshold", SILENCE_THRESHOLD)
        silence_duration = config.get("silence_duration", SILENCE_DURATION)
        max_seconds = config.get("max_record_seconds", MAX_RECORD_SECONDS)

        stream = self.pa.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK,
        )

        frames = []
        silent_chunks = 0
        chunks_per_second = SAMPLE_RATE / CHUNK
        max_silent_chunks = int(silence_duration * chunks_per_second)
        max_chunks = int(max_seconds * chunks_per_second)
        has_speech = False

        try:
            for i in range(max_chunks):
                # Manuel durdurma kontrolü
                if self.stop_requested.is_set():
                    break

                data = stream.read(CHUNK, exception_on_overflow=False)
                frames.append(data)

                # RMS hesapla
                audio_data = np.frombuffer(data, dtype=np.int16).astype(np.float32)
                rms = np.sqrt(np.mean(audio_data ** 2))

                if rms > silence_threshold:
                    silent_chunks = 0
                    has_speech = True
                else:
                    silent_chunks += 1

                # Konuşma başladıktan sonra sessizlik süresi dolunca dur
                if has_speech and silent_chunks >= max_silent_chunks:
                    break
        finally:
            stream.stop_stream()
            stream.close()

        # WAV olarak döndür
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(self.pa.get_sample_size(FORMAT))
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b"".join(frames))
        return buf.getvalue()

    # ── UI Oluştur ──

    def _build_ui(self):
        root = self.root

        # ── Başlık Çubuğu ──
        header = tk.Frame(root, bg=COLORS["surface"], height=36)
        header.pack(fill="x", padx=0, pady=0)
        header.pack_propagate(False)

        tk.Label(
            header,
            text="🎙️ Voice Paste",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("Segoe UI", 10, "bold"),
        ).pack(side="left", padx=10)

        # Pin butonu (always on top toggle)
        self.pin_var = tk.BooleanVar(value=True)
        self.pin_btn = tk.Label(
            header,
            text="📌",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("Segoe UI", 10),
            cursor="hand2",
        )
        self.pin_btn.pack(side="right", padx=8)
        self.pin_btn.bind("<Button-1>", self.toggle_pin)

        # ── Durum Göstergesi ──
        status_frame = tk.Frame(root, bg=COLORS["bg"])
        status_frame.pack(fill="x", padx=16, pady=(14, 6))

        self.status_dot = tk.Canvas(
            status_frame, width=10, height=10, bg=COLORS["bg"], highlightthickness=0
        )
        self.status_dot.pack(side="left")
        self.status_dot.create_oval(1, 1, 9, 9, fill=COLORS["success"], outline="")

        self.status_label = tk.Label(
            status_frame,
            text="  Hazır",
            bg=COLORS["bg"],
            fg=COLORS["success"],
            font=("Segoe UI", 9),
        )
        self.status_label.pack(side="left")

        # ── Büyük Mikrofon Butonu ──
        btn_frame = tk.Frame(root, bg=COLORS["bg"])
        btn_frame.pack(pady=(10, 8))

        self.mic_btn = tk.Canvas(
            btn_frame,
            width=80,
            height=80,
            bg=COLORS["bg"],
            highlightthickness=0,
            cursor="hand2",
        )
        self.mic_btn.pack()
        self._draw_mic_button(COLORS["accent"])
        self.mic_btn.bind("<Button-1>", lambda e: self.toggle_listening())
        self.mic_btn.bind("<Enter>", lambda e: self._draw_mic_button(COLORS["accent_hover"]) if not self.is_listening else None)
        self.mic_btn.bind("<Leave>", lambda e: self._draw_mic_button(COLORS["accent"]) if not self.is_listening else None)

        # Kısayol bilgisi
        hotkey_text = self.config["hotkey"].replace("+", " + ").upper()
        tk.Label(
            root,
            text=f"veya  {hotkey_text}",
            bg=COLORS["bg"],
            fg=COLORS["text_dim"],
            font=("Segoe UI", 8),
        ).pack(pady=(0, 8))

        # ── Son Algılanan Metin ──
        text_frame = tk.Frame(root, bg=COLORS["border"], padx=1, pady=1)
        text_frame.pack(fill="x", padx=16, pady=(0, 8))

        text_inner = tk.Frame(text_frame, bg=COLORS["surface"])
        text_inner.pack(fill="both")

        tk.Label(
            text_inner,
            text="Son algılanan:",
            bg=COLORS["surface"],
            fg=COLORS["text_dim"],
            font=("Segoe UI", 7),
            anchor="w",
        ).pack(fill="x", padx=8, pady=(4, 0))

        self.result_label = tk.Label(
            text_inner,
            text="—",
            bg=COLORS["surface"],
            fg=COLORS["text"],
            font=("Segoe UI", 9),
            anchor="w",
            wraplength=230,
            justify="left",
        )
        self.result_label.pack(fill="x", padx=8, pady=(0, 6))

        # ── Alt Kontroller ──
        controls = tk.Frame(root, bg=COLORS["bg"])
        controls.pack(fill="x", padx=16, pady=(0, 4))

        # Dil seçimi
        tk.Label(
            controls, text="Dil:", bg=COLORS["bg"], fg=COLORS["text_dim"], font=("Segoe UI", 8)
        ).pack(side="left")

        self.lang_var = tk.StringVar(value=self.config["language"])
        lang_menu = ttk.Combobox(
            controls,
            textvariable=self.lang_var,
            values=list(LANG_MAP.keys()),
            width=4,
            state="readonly",
            font=("Segoe UI", 8),
        )
        lang_menu.pack(side="left", padx=(4, 8))
        lang_menu.bind("<<ComboboxSelected>>", self.on_lang_change)

        # Auto-enter toggle
        self.auto_enter_var = tk.BooleanVar(value=self.config["auto_enter"])
        ae_check = tk.Checkbutton(
            controls,
            text="Auto Enter",
            variable=self.auto_enter_var,
            bg=COLORS["bg"],
            fg=COLORS["text_dim"],
            selectcolor=COLORS["surface"],
            activebackground=COLORS["bg"],
            activeforeground=COLORS["text"],
            font=("Segoe UI", 8),
            command=self.on_auto_enter_change,
        )
        ae_check.pack(side="right")

        # ── Model Seçimi ──
        model_frame = tk.Frame(root, bg=COLORS["bg"])
        model_frame.pack(fill="x", padx=16, pady=(0, 4))

        tk.Label(
            model_frame, text="Model:", bg=COLORS["bg"], fg=COLORS["text_dim"], font=("Segoe UI", 8)
        ).pack(side="left")

        self.model_var = tk.StringVar(value=self.config.get("whisper_model", "base"))
        model_menu = ttk.Combobox(
            model_frame,
            textvariable=self.model_var,
            values=["tiny", "base", "small", "medium"],
            width=7,
            state="readonly",
            font=("Segoe UI", 8),
        )
        model_menu.pack(side="left", padx=(4, 8))
        model_menu.bind("<<ComboboxSelected>>", self.on_model_change)

        tk.Label(
            model_frame, text="(küçük=hızlı, büyük=doğru)",
            bg=COLORS["bg"], fg=COLORS["text_dim"], font=("Segoe UI", 7)
        ).pack(side="left")

        # ── Alt bilgi ──
        tk.Label(
            root,
            text=f"Çıkış: {self.config['exit_hotkey'].upper().replace('+', ' + ')}",
            bg=COLORS["bg"],
            fg=COLORS["text_dim"],
            font=("Segoe UI", 7),
        ).pack(side="bottom", pady=(0, 6))

    def _draw_mic_button(self, color, icon=None):
        """Yuvarlak mikrofon butonunu çiz."""
        c = self.mic_btn
        c.delete("all")
        # Daire
        c.create_oval(4, 4, 76, 76, fill=color, outline="")
        # İkon
        symbol = icon or ("⏹" if self.is_listening else "🎤")
        c.create_text(40, 38, text=symbol, font=("Segoe UI", 22), fill="white")

    def _position_bottom_right(self):
        """Pencereyi sağ alt köşeye konumlandır."""
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        w = self.root.winfo_width()
        h = self.root.winfo_height()
        x = sw - w - 20
        y = sh - h - 60
        self.root.geometry(f"+{x}+{y}")

    # ── System Tray ──

    def _create_tray_image(self):
        """Tray ikonu için küçük bir mikrofon resmi oluştur."""
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        # Mor daire arka plan
        draw.ellipse([2, 2, size - 2, size - 2], fill="#7c3aed")
        # Beyaz mikrofon simgesi (basit oval + çubuk)
        draw.rounded_rectangle([22, 12, 42, 36], radius=8, fill="white")
        draw.rectangle([30, 36, 34, 46], fill="white")
        draw.arc([20, 26, 44, 50], start=0, end=180, fill="white", width=3)
        return img

    def _setup_tray(self):
        """Sistem tepsisi ikonunu oluştur."""
        image = self._create_tray_image()
        menu = pystray.Menu(
            pystray.MenuItem("Göster", self._tray_show, default=True),
            pystray.MenuItem("Dinle", self._tray_listen),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Çıkış", self._tray_quit),
        )
        self.tray_icon = pystray.Icon("VoicePaste", image, "Voice Paste", menu)
        # Tray'i ayrı thread'de çalıştır
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()

    def minimize_to_tray(self):
        """Pencereyi gizle, tray'de kalsın."""
        self.root.withdraw()

    def _tray_show(self, icon=None, item=None):
        """Tray'den pencereyi tekrar göster."""
        self.root.after(0, self._restore_window)

    def _restore_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _tray_listen(self, icon=None, item=None):
        """Tray menüsünden dinlemeyi başlat/durdur."""
        self.root.after(0, self.toggle_listening)

    def _tray_quit(self, icon=None, item=None):
        """Tray'den tamamen çık."""
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.after(0, self.on_close)

    # ── Hotkey ──

    def _setup_hotkey(self):
        keyboard.add_hotkey(
            self.config["hotkey"],
            lambda: self.root.after(0, self.toggle_listening),
        )
        keyboard.add_hotkey(
            self.config["exit_hotkey"],
            lambda: self.root.after(0, self.on_close),
        )

    # ── Durum Güncelle ──

    def _set_status(self, text, color):
        self.status_dot.delete("all")
        self.status_dot.create_oval(1, 1, 9, 9, fill=color, outline="")
        self.status_label.config(text=f"  {text}", fg=color)

    # ── Dinle & Yapıştır ──

    def toggle_listening(self):
        """Butona/kısayola basınca: dinlemiyorsa başlat, dinliyorsa durdur."""
        if self.is_listening:
            self.stop_listening()
        else:
            self.start_listening()

    def stop_listening(self):
        """Kaydi durdur — worker thread flag'i görüp transcribe'a geçecek."""
        self.stop_requested.set()
        self._set_status("Durduruluyor...", COLORS["warning"])

    def start_listening(self):
        if self.is_listening or self.model_loading:
            return
        self.stop_requested.clear()
        self.is_listening = True
        self._set_status("Dinleniyor... (tekrar bas = durdur)", COLORS["recording"])
        self._draw_mic_button(COLORS["recording"])
        self.result_label.config(text="🎤 Konuşun... (bitince butona veya kısayola tekrar basın)")

        thread = threading.Thread(target=self._listen_worker, daemon=True)
        thread.start()

    def _listen_worker(self):
        config = self.config

        if self.whisper_model is None:
            self.root.after(0, lambda: self._set_status("Model yüklenmedi!", COLORS["recording"]))
            self.root.after(0, lambda: self.result_label.config(text="❌ Whisper modeli henüz yüklenmedi"))
            winsound.Beep(400, 300)
            self.is_listening = False
            self.root.after(0, lambda: self._draw_mic_button(COLORS["accent"]))
            return

        try:
            if config["beep_on_ready"]:
                winsound.Beep(800, 150)

            # Ses kaydet (sessizlik algılanınca otomatik durur)
            wav_data = self._record_audio()

            if len(wav_data) < 5000:  # Çok kısa kayıt
                self.root.after(0, lambda: self._set_status("Çok kısa!", COLORS["warning"]))
                self.root.after(0, lambda: self.result_label.config(text="⏰ Yeterli ses algılanamadı"))
                winsound.Beep(400, 200)
                return

            self.root.after(0, lambda: self._set_status("Çevriliyor...", COLORS["warning"]))
            self.root.after(0, lambda: self.result_label.config(text="⏳ Whisper işliyor..."))

            # Geçici WAV dosyasına yaz →  Whisper'a ver
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(wav_data)
                tmp_path = tmp.name

            try:
                lang = config.get("language", "tr")
                # Whisper'a hint: Bu Türkçe konuşma, İngilizce kelimeleri de tanı
                prompt_hint = "Bu Türkçe konuşmadır." if lang == "tr" else "This is English speech."
                
                segments, info = self.whisper_model.transcribe(
                    tmp_path,
                    language=lang,
                    initial_prompt=prompt_hint,
                    beam_size=2,
                    vad_filter=True,
                    vad_parameters=dict(
                        min_silence_duration_ms=400,
                        speech_pad_ms=500,
                    ),
                    temperature=[0.0, 0.2, 0.4],
                )
                text = " ".join(seg.text.strip() for seg in segments).strip()
                text = self._post_process_text(text, lang)
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

            if not text:
                self.root.after(0, lambda: self._set_status("Anlaşılamadı", COLORS["warning"]))
                self.root.after(0, lambda: self.result_label.config(text="❌ Konuşma algılanamadı"))
                winsound.Beep(400, 300)
                return

            # Yapıştır
            pyperclip.copy(text)
            time.sleep(config["paste_delay"])
            pyautogui.hotkey("ctrl", "v")

            if config["auto_enter"]:
                time.sleep(0.1)
                pyautogui.press("enter")

            winsound.Beep(1200, 100)

            display = text if len(text) <= 100 else text[:97] + "..."
            self.root.after(0, lambda: self.result_label.config(text=display))
            self.root.after(0, lambda: self._set_status("Hazır", COLORS["success"]))

        except Exception as e:
            err_msg = str(e)
            self.root.after(0, lambda: self._set_status("Hata", COLORS["recording"]))
            self.root.after(0, lambda: self.result_label.config(text=f"❌ {err_msg}"))
            winsound.Beep(400, 300)
        finally:
            self.is_listening = False
            self.root.after(0, lambda: self._draw_mic_button(COLORS["accent"]))

    # ── Olaylar ──

    def toggle_pin(self, event=None):
        val = not self.pin_var.get()
        self.pin_var.set(val)
        self.root.attributes("-topmost", val)
        self.pin_btn.config(text="📌" if val else "📍")

    def on_lang_change(self, event=None):
        self.config["language"] = self.lang_var.get()
        save_config(self.config)

    def on_auto_enter_change(self):
        self.config["auto_enter"] = self.auto_enter_var.get()
        save_config(self.config)

    def _post_process_text(self, text: str, lang: str) -> str:
        """
        Türkçe-İngilizce karışık metni temizle.
        Sık yapılan Whisper hatalarını düzelt.
        """
        if lang != "tr":
            return text
        
        # Sık hata düzeltmeleri
        corrections = {
            " ay ": " ai ",  # "high" → "hai" yerine "ay"
            " high": " hai",
            "highline": "hayyoline",
            "hello": "hele",  # İngilizce kelimeleri context'e göre düzelt
        }
        
        for wrong, right in corrections.items():
            text = text.replace(wrong, right)
        
        return text
    
    def on_model_change(self, event=None):
        new_model = self.model_var.get()
        if new_model != self.config.get("whisper_model"):
            self.config["whisper_model"] = new_model
            save_config(self.config)
            self.whisper_model = None
            self.root.after(0, lambda: self._set_status("Model değişiyor...", COLORS["warning"]))
            self._load_model_async()

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

    # ── Çalıştır ──

    def run(self):
        self.root.mainloop()


# ─── Giriş Noktası ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = VoicePasteApp()
    app.run()
