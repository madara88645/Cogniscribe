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

## Troubleshooting

- `TypeError: Cannot read properties of undefined (reading 'on')` in `dev:electron`:
  - Cause: global `ELECTRON_RUN_AS_NODE` is set.
  - Quick fix (current terminal): `set ELECTRON_RUN_AS_NODE=`
  - Permanent fix: remove global `ELECTRON_RUN_AS_NODE` from system/user environment variables.

- `Backend request timeout: ping` on startup:
  - Increase backend init timeout:
    - `set VP_BACKEND_PING_TIMEOUT_MS=90000`
    - then run `npm run dev` again.

- `Error: Port 5173 is already in use`:
  - `npm run dev` now auto-frees port `5173` on Windows before starting Vite.
  - If it still fails, close old dev terminals and run `npm run dev` again.
