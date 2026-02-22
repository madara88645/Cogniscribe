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
    "language": "en",
    "hotkey": "ctrl+shift+space",
    "auto_enter": false,
    "paste_delay": 0.5,
    "beep_on_ready": true,
    "exit_hotkey": "ctrl+shift+q",
    
    "whisper_model": "base",
    "silence_threshold": 500,
    "silence_duration": 1.2,
    "max_record_seconds": 60,
    "min_record_seconds": 0.3,
    "enable_multilingual": true,
    "post_recording_delay": 0.5
}
```

### Configuration Options

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `language` | string | `"en"` | Language code (e.g., `"en"`, `"tr"`, `"de"`, `"fr"`, `"ja"`) |
| `hotkey` | string | `"ctrl+shift+space"` | Hotkey to trigger recording |
| `auto_enter` | boolean | `false` | Auto-press Enter after pasting |
| `paste_delay` | float | `0.5` | Delay before pasting (seconds) - increased to prevent duplicate pastes |
| `beep_on_ready` | boolean | `true` | Audio feedback when recording starts |
| `exit_hotkey` | string | `"ctrl+shift+q"` | Hotkey to exit application |
| `whisper_model` | string | `"base"` | Model size: `"tiny"` (fastest), `"base"` (balanced), `"small"`, `"medium"` (most accurate) |
| `silence_threshold` | int | `500` | RMS threshold for silence detection (lower = more sensitive) |
| `silence_duration` | float | `1.2` | Seconds of silence to auto-stop recording |
| `max_record_seconds` | int | `60` | Maximum recording duration |
| `min_record_seconds` | float | `0.3` | Minimum recording duration (prevents accidental short triggers) |
| `enable_multilingual` | boolean | `true` | Auto-detect language from speech |
| `post_recording_delay` | float | `0.5` | Delay after recording before processing (stabilizes clipboard) |

### Recommended Settings for Quality

**For Best Accuracy** (slower, uses more RAM):
```json
{
    "whisper_model": "small",
    "silence_threshold": 400,
    "paste_delay": 0.8,
    "post_recording_delay": 1.0
}
```

**For Speed + Quality** (balanced):
```json
{
    "whisper_model": "base",
    "silence_threshold": 500,
    "paste_delay": 0.5,
    "post_recording_delay": 0.5
}
```

**For Noisy Environments**:
```json
{
    "silence_threshold": 800,
    "silence_duration": 2.0,
    "min_record_seconds": 0.5
}
```

**To Prevent Duplicate Pastes**:
Increase `paste_delay` to `0.8` or `1.0`:
```json
{
    "paste_delay": 1.0,
    "post_recording_delay": 0.5
}
```

### Supported Languages

Cogniscribe uses Whisper and supports 100+ languages:

```
Arabic (ar), Bengali (bn), Chinese Simplified (zh), Chinese Traditional (zh-TW),
Dutch (nl), English (en), French (fr), German (de), Greek (el), Hindi (hi),
Hungarian (hu), Indonesian (id), Italian (it), Japanese (ja), Korean (ko),
Marathi (mr), Polish (pl), Portuguese (pt), Russian (ru), Spanish (es),
Swedish (sv), Tamil (ta), Telugu (te), Thai (th), Turkish (tr), 
Ukrainian (uk), Urdu (ur), Vietnamese (vi), and more...
```

---

## Performance & Troubleshooting

### Improving Transcription Accuracy

1. **Upgrade the Whisper Model** — Use larger models for better accuracy:
   ```json
   "whisper_model": "small"    // Better than base, uses ~475MB
   "whisper_model": "medium"   // Highest accuracy, uses ~1.5GB
   ```

2. **Reduce Background Noise** — Work in a quiet environment or wear a noise-canceling headset

3. **Speak Clearly** — Enunciate words clearly and at a normal pace (not too fast)

4. **Adjust Silence Detection**:
   - For quiet environments: Lower `silence_threshold` (300-400)
   - For noisy environments: Raise `silence_threshold` (600-1000)

### Fixing Duplicate Paste Issues

**Problem: Text pastes multiple times**
- **Solution 1**: Increase `paste_delay` to `0.8-1.0`
- **Solution 2**: Increase `post_recording_delay` to avoid clipboard conflicts
- **Solution 3**: Don't tap hotkey repeatedly; wait for beep before speaking

**Problem: Text doesn't paste**
- Ensure target application is in focus when pasting
- Some applications may block automated input; check application permissions
- Try increasing `paste_delay`

### Fixing Speech Recognition Issues

**Problem: "Transcription failed" errors**
- Check internet connection (some models require it initially for download)
- Ensure microphone is properly connected and set as default device in Windows Sound Settings
- Try `"whisper_model": "tiny"` first to verify setup works

**Problem: Wrong language detected**
- Set `"enable_multilingual": false` and specify language code
- For Turkish: `"language": "tr"`
- For Spanish: `"language": "es"`

**Problem: Background noise interference**
- Increase `silence_threshold` to 800-1200
- Work in a quieter environment
- Use `"silence_duration": 2.0` for longer silence periods

---

## Tips & Tricks

🎯 **VS Code Integration** — Open editor, click input area, press `Ctrl+Shift+Space`, speak your code  

🎯 **Chat Applications** — Works with Discord, Teams, Slack, Gmail, browser-based chat  

🎯 **Auto-Send Messages** — Set `"auto_enter": true` to auto-press Enter after pasting  

🎯 **Keyboard Shortcuts** — Change hotkey in `config.json` to any key combo (e.g., `"alt+space"`)  

🎯 **Model Selection**:
   - Use `"tiny"` for fast feedback on low-end machines
   - Use `"base"` for balanced speed/accuracy (default)
   - Use `"small"` or `"medium"` for best accuracy on powerful machines

🎯 **Multiple Languages** — Leave `"enable_multilingual": true` to auto-detect speech language

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
