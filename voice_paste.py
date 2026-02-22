"""
Voice Paste - Sesli Komut ile Metin Yapıştırma Aracı
=====================================================
Mikrofondan sesi alır, metne çevirir ve aktif pencereye yapıştırır.
Kısayol tuşu ile tetiklenir (varsayılan: Ctrl+Shift+Space).

Kullanım:
    python voice_paste.py          -> Sürekli mod (kısayol ile tetikle)
    python voice_paste.py --once   -> Tek seferlik dinle ve yapıştır
"""

import json
import os
import sys
import time
import threading
import winsound

import speech_recognition as sr
import pyautogui
import pyperclip
import keyboard


# ─── Konfigürasyon ────────────────────────────────────────────────────────────

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "language": "tr-TR",
    "hotkey": "ctrl+shift+space",
    "auto_enter": False,
    "paste_delay": 0.4,
    "ambient_noise_duration": 0.5,
    "energy_threshold": None,
    "beep_on_ready": True,
    "continuous_mode": True,
    "exit_hotkey": "ctrl+shift+q",
}


def load_config() -> dict:
    """config.json dosyasını oku, yoksa varsayılanları kullan."""
    config = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
            config.update(user_cfg)
        except Exception as e:
            print(f"[!] config.json okunamadı, varsayılanlar kullanılıyor: {e}")
    return config


# ─── Yardımcı Fonksiyonlar ────────────────────────────────────────────────────

def beep_ready():
    """Dinlemeye hazır olduğunu belirten kısa bip sesi."""
    winsound.Beep(800, 150)


def beep_done():
    """İşlem tamamlandı bip sesi."""
    winsound.Beep(1200, 100)


def beep_error():
    """Hata bip sesi."""
    winsound.Beep(400, 300)


def paste_to_active_window(text: str, config: dict):
    """
    Metni panoya kopyalar ve aktif pencereye Ctrl+V ile yapıştırır.
    auto_enter=True ise sonuna Enter da basar.
    """
    pyperclip.copy(text)
    time.sleep(config["paste_delay"])
    pyautogui.hotkey("ctrl", "v")

    if config["auto_enter"]:
        time.sleep(0.1)
        pyautogui.press("enter")


# ─── Ana İşlev ────────────────────────────────────────────────────────────────

def listen_and_paste(config: dict):
    """Mikrofondan dinle, metne çevir, aktif pencereye yapıştır."""
    recognizer = sr.Recognizer()

    # Enerji eşiği ayarı (None ise otomatik)
    if config["energy_threshold"] is not None:
        recognizer.energy_threshold = config["energy_threshold"]
        recognizer.dynamic_energy_threshold = False

    try:
        with sr.Microphone() as source:
            # Arka plan gürültüsüne kalibrasyon
            recognizer.adjust_for_ambient_noise(
                source, duration=config["ambient_noise_duration"]
            )

            if config["beep_on_ready"]:
                beep_ready()
            print("\n🎤  Konuşun...")

            audio = recognizer.listen(source, timeout=10, phrase_time_limit=30)

        print("⏳  Metne çevriliyor...")
        text = recognizer.recognize_google(audio, language=config["language"])
        print(f"✅  Algılanan: {text}")

        paste_to_active_window(text, config)
        beep_done()

    except sr.WaitTimeoutError:
        print("⏰  Zaman aşımı — ses algılanamadı.")
        beep_error()
    except sr.UnknownValueError:
        print("❌  Ses anlaşılamadı.")
        beep_error()
    except sr.RequestError as e:
        print(f"❌  Google servisine ulaşılamadı: {e}")
        beep_error()
    except Exception as e:
        print(f"❌  Beklenmeyen hata: {e}")
        beep_error()


# ─── Sürekli Mod (Hotkey ile Tetikleme) ───────────────────────────────────────

def run_continuous(config: dict):
    """
    Arka planda çalışır. Kısayol tuşuna basıldığında dinlemeyi başlatır.
    Çıkış kısayolu ile sonlandırılır.
    """
    hotkey = config["hotkey"]
    exit_hotkey = config["exit_hotkey"]
    is_listening = threading.Event()

    def on_hotkey():
        if is_listening.is_set():
            return  # Zaten dinliyor
        is_listening.set()
        try:
            listen_and_paste(config)
        finally:
            is_listening.clear()

    print("=" * 55)
    print("  🎙️  Voice Paste — Sesli Yapıştırma Aracı")
    print("=" * 55)
    print(f"  Dil          : {config['language']}")
    print(f"  Dinle        : {hotkey}")
    print(f"  Çıkış        : {exit_hotkey}")
    print(f"  Oto-Enter    : {'Evet' if config['auto_enter'] else 'Hayır'}")
    print("=" * 55)
    print("  Bekleniyor... Kısayola basın.\n")

    keyboard.add_hotkey(hotkey, lambda: threading.Thread(target=on_hotkey, daemon=True).start())
    keyboard.wait(exit_hotkey)

    print("\n👋  Voice Paste kapatıldı.")


# ─── Tek Seferlik Mod ─────────────────────────────────────────────────────────

def run_once(config: dict):
    """Tek sefer dinle, yapıştır ve çık."""
    print("🎙️  Voice Paste — Tek Seferlik Mod")
    print("    3 saniye içinde aktif pencereye geçin...\n")
    time.sleep(3)
    listen_and_paste(config)


# ─── Giriş Noktası ────────────────────────────────────────────────────────────

def main():
    config = load_config()

    if "--once" in sys.argv:
        run_once(config)
    else:
        run_continuous(config)


if __name__ == "__main__":
    main()
