# Voice Paste

Voice Paste is a local Windows dictation app:
- Record from microphone
- Transcribe with faster-whisper
- Paste into the active app

This version includes:
- Shared STT pipeline (`stt_service.py`) for all entrypoints
- Electron + React + Tailwind compact desktop UI
- Python backend service over line-delimited JSON-RPC (`backend_service.py`)
- Config migration and telemetry logging

## Run (Electron UI)

```bash
cd desktop
npm install
npm run dev
```

Or from project root:

```bash
start.bat
```

## Run (Python CLI)

```bash
pip install -r requirements.txt
python voice_paste.py
python voice_paste.py --once
```

## Legacy Tkinter Fallback

```bash
start_legacy.bat
```

## Build Portable EXE

```bash
cd desktop
npm run dist:portable
```

Output path:
- `desktop/release/`

## Architecture

- `backend_service.py`: audio capture, STT, confidence gate, paste, telemetry
- `desktop/electron/main.ts`: app lifecycle, tray, hotkeys, backend process
- `desktop/electron/preload.ts`: secure bridge API (`window.voicePaste.*`)
- `desktop/renderer/`: React TypeScript Tailwind UI

## Config Highlights (`config.json`)

- `stt.*`: model/profile/language/confidence behavior
- `audio.*`: preprocessing and silence behavior
- `telemetry.*`: JSONL metrics output
- `ui.*`: window size, always-on-top, theme/density/motion

## Default Hotkeys

- Record toggle: `Ctrl+Shift+Space`
- Exit app: `Ctrl+Shift+Q`

## Notes

- STT is local/offline by default.
- GPU fallback to CPU is automatic when CUDA load fails.
- Low-confidence handling is configurable (`allow_low_confidence_paste`, floors, retry).
