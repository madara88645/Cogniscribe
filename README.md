# Cogniscribe 🎙️

A powerful Windows utility that captures audio from your microphone, converts it to text using advanced speech recognition, and automatically pastes it into the active window (VS Code, browsers, text editors, etc.).

**Cogniscribe** enables hands-free text input through voice commands, with intelligent silence detection, multi-language support, and customizable hotkeys.

---

## Features

✨ **Hotkey-Triggered Recording** — Press `Ctrl+Shift+Space` to start/stop listening  
✨ **Automatic Text Insertion** — Seamlessly pastes transcribed text into active applications  
✨ **Multi-Language Support** — Supports 100+ languages via Faster-Whisper AI model  
✨ **Continuous Mode** — Runs in background, ready to capture on hotkey press  
✨ **One-Shot Mode** — Use `--once` flag for single-use transcription  
✨ **Audio Feedback** — Beep notifications for ready/recording/error states  
✨ **Highly Configurable** — Customize all settings via `config.json`  
✨ **Silence Detection** — Automatically stops recording after silence threshold  
✨ **Low Latency** — Fast transcription with support for both base and larger AI models  

---

## System Requirements

- **OS:** Windows 10/11 or later
- **Python:** 3.8 or higher
- **Hardware:** Microphone/audio input device
- **Storage:** ~500MB for Whisper models
- **RAM:** 2GB minimum (4GB+ recommended)

---

## Installation

### 1. Clone or Download the Repository

```bash
git clone https://github.com/madara88645/Cogniscribe.git
cd Cogniscribe
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ **PyAudio Installation Note**  
> If you encounter issues installing PyAudio on Windows:
> ```bash
> pip install pipwin
> pipwin install pyaudio
> ```

---

## Quick Start

### Option 1: GUI (Easiest)
Double-click **`start.bat`** to launch Cogniscribe in continuous mode.

### Option 2: One-Shot Mode
Double-click **`start_once.bat`** to record once and exit.

### Option 3: Command Line
```bash
# Continuous mode (listen on hotkey)
python voice_paste.py

# One-shot mode (record once)
python voice_paste.py --once
```

---

## Usage

### Default Hotkeys

| Hotkey | Action |
|---|---|
| `Ctrl+Shift+Space` | Start/Stop listening |
| `Ctrl+Shift+Q` | Exit application |

---

## Configuration (`config.json`)

Customize Cogniscribe's behavior by editing `config.json`:

```json
{
    "language": "en",                  // Language code (en, tr, de, fr, etc.)
    "hotkey": "ctrl+shift+space",      // Primary recording hotkey
    "auto_enter": false,               // Auto-press Enter after pasting
    "paste_delay": 0.3,                // Delay before pasting (seconds)
    "beep_on_ready": true,             // Beep sound when ready to record
    "exit_hotkey": "ctrl+shift+q",     // Hotkey to exit application
    "whisper_model": "base",           // AI model size (tiny, base, small, medium)
    "silence_threshold": 500,          // Silence detection threshold
    "silence_duration": 1.2,           // Silence duration to stop recording (seconds)
    "max_record_seconds": 60,          // Maximum recording duration
    "enable_multilingual": true        // Enable multi-language support
}
```

### Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `language` | string | `"en"` | Language code for speech recognition (e.g., `"en"`, `"tr"`, `"de"`, `"fr"`) |
| `hotkey` | string | `"ctrl+shift+space"` | Hotkey combination to trigger recording |
| `auto_enter` | boolean | `false` | Automatically press Enter after pasting text |
| `paste_delay` | float | `0.3` | Delay (in seconds) before pasting transcribed text |
| `beep_on_ready` | boolean | `true` | Play beep sound when recording starts/stops |
| `exit_hotkey` | string | `"ctrl+shift+q"` | Hotkey to exit the application |
| `whisper_model` | string | `"base"` | Whisper model size: `"tiny"` (fast), `"base"`, `"small"`, `"medium"` (accurate) |
| `silence_threshold` | int | `500` | Silence detection threshold (lower = more sensitive) |
| `silence_duration` | float | `1.2` | Seconds of silence needed to auto-stop recording |
| `max_record_seconds` | int | `60` | Maximum recording duration in seconds |
| `enable_multilingual` | boolean | `true` | Enable automatic language detection |

### Supported Languages

Cogniscribe supports 100+ languages. Here are some common ones:

```
Arabic (ar), Chinese Simplified (zh), Chinese Traditional (zh-TW),
Dutch (nl), English (en), French (fr), German (de), Hindi (hi),
Indonesian (id), Italian (it), Japanese (ja), Korean (ko),
Polish (pl), Portuguese (pt), Russian (ru), Spanish (es),
Swedish (sv), Thai (th), Turkish (tr), Ukrainian (uk), Vietnamese (vi)
```

---

## Tips & Tricks

🎯 **VS Code Integration** — Open your code editor, click in the editor, press `Ctrl+Shift+Space`, and speak your code comments or text  

🎯 **Chat Applications** — Works with Discord, Teams, Slack, Gmail, and any web application  

🎯 **Auto-Confirm** — Set `"auto_enter": true` to automatically send messages after transcription  

🎯 **Noisy Environments** — Adjust `silence_threshold` (300-4000) to filter out background noise  

🎯 **Larger Model for Better Accuracy** — Change `"whisper_model"` to `"small"` or `"medium"` (requires more VRAM)  

🎯 **Customize Paste Timing** — Increase `paste_delay` if text appears before cursor focus is ready  

---

## Troubleshooting

**Issue: "PyAudio not found" error**
```bash
pip install pipwin
pipwin install pyaudio
```

**Issue: Microphone not detected**
- Ensure your microphone is plugged in and set as the default device in Windows Sound Settings
- Check Device Manager to confirm the microphone is recognized

**Issue: Poor transcription accuracy**
- Use a better microphone or reduce background noise
- Increase `whisper_model` to `"small"` or `"medium"` for higher accuracy
- Speak clearly and at a normal pace

**Issue: Text isn't pasting**
- Ensure the target application window is in focus
- Some applications (like certain IDEs) may require additional permissions
- Try increasing `paste_delay` in `config.json`

**Issue: Hotkey not working**
- Check if another application is using the same hotkey
- Try a different hotkey combination in `config.json`
- Restart the application after changing the hotkey

---

## Project Structure

```
Cogniscribe/
├── voice_paste.py         # Main CLI application
├── voice_paste_gui.py     # GUI launcher (optional)
├── config.json            # Configuration file
├── requirements.txt       # Python dependencies
├── start.bat             # Batch file for continuous mode
├── start_once.bat        # Batch file for one-shot mode
├── VoicePaste.vbs        # VBS script for Windows shortcut
└── README.md             # This file
```

---

## Technologies Used

- **[Faster-Whisper](https://github.com/SYSTRAN/faster-whisper)** — Fast and accurate speech-to-text
- **[PyAudio](https://people.csail.mit.edu/hubert/pyaudio/)** — Audio recording
- **[PyAutoGUI](https://pyautogui.readthedocs.io/)** — Simulate keyboard/mouse input
- **[PyPerclip](https://github.com/asweigart/pyperclip)** — Clipboard management
- **[Keyboard](https://github.com/boppreh/keyboard)** — Global hotkey listening

---

## Performance Notes

- **First Run:** The application downloads the Whisper model (~139MB for 'base'). This happens automatically.
- **Model Sizes:**
  - `tiny` (39M) — Fastest, lower accuracy
  - `base` (139M) — Good balance (default)
  - `small` (465M) — Better accuracy, moderate speed
  - `medium` (1.5G) — Highest accuracy, slower

---

## Contributing

Found a bug or have a feature request? Feel free to:
1. Open an [issue](https://github.com/madara88645/Cogniscribe/issues)
2. Fork the repository and submit a pull request
3. Suggest improvements or optimizations

---

## License

This project is open-source and available under the MIT License. See LICENSE file for details.

---

## Author

**madara88645**  
Email: mehmet.ozel2701@gmail.com  
GitHub: [@madara88645](https://github.com/madara88645)

---

## Support & Contact

If you encounter any issues or have questions:
- 📧 Open an issue on [GitHub Issues](https://github.com/madara88645/Cogniscribe/issues)
- 💬 Submit feedback via email

---

**Happy transcribing! 🎙️✨**
