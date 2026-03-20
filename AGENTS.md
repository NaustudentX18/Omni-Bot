# AGENTS.md

## Cursor Cloud specific instructions

### Overview

Omni-Bot is a Python 3.10+ AI companion / cyberpunk pentesting assistant designed for Raspberry Pi Zero 2 W. On x86_64 dev machines, hardware-dependent features (LCD, GPIO buttons, audio, PiSugar battery) fail gracefully — all non-hardware paths work normally.

### Virtual environment

The project uses a venv at `/workspace/venv`. Always activate it before running commands:

```bash
source /workspace/venv/bin/activate
```

### Running tests

```bash
python -m pytest tests/ -v
```

48 tests across 3 files cover all features. Some tests (`test_full_auto_reports_hostname_target_error_cleanly`) depend on `config/config.ini` having `god_mode = false`. If a prior demo or test mutated that file, reset it with `git checkout config/config.ini` before re-running tests.

### Linting

See `pyproject.toml` for tool configs. Commands: `ruff check .`, `black --check .`, `mypy jarvis_bud/ nxtgenai/`, `bandit -r jarvis_bud/ nxtgenai/ -c pyproject.toml`.

### Running the application

The full `python main.py` requires Raspberry Pi hardware. On x86_64 use:

- **Export mode:** `python main.py export` — generates an HTML report + encrypted ZIP without hardware.
- **Web dashboard:** Start with `python -c "from jarvis_bud.web import start_dashboard; start_dashboard()"` on port 8080.
- **Module-level testing:** Import `JarvisBud` and call `_execute_voice_intent()` directly.

### Architecture (new modules)

| Module | Purpose |
|--------|---------|
| `jarvis_bud/hardware/stt.py` | Offline STT via faster-whisper tiny model |
| `jarvis_bud/hardware/tts.py` | Piper TTS with cyberpunk voice + espeak fallback |
| `jarvis_bud/web/` | Flask dashboard on port 8080 with matrix rain UI |
| `jarvis_bud/updater.py` | Git-based OTA self-update with rollback |
| `jarvis_bud/plugins/` | Hot-loadable plugin system (tools + voice commands) |
| `jarvis_bud/sync.py` | Zeroconf multi-device sync over LAN |

### Key gotchas

- `llama-cpp-python` builds from source during `pip install` — requires `build-essential` and `python3-dev` system packages.
- `sentence-transformers` and `torch` are large downloads (~2 GB total); installs may take several minutes.
- RPi-only dependencies (`RPi.GPIO`, `pyalsaaudio`, `pyaudio`) are platform-gated in `requirements.txt` and skipped on x86_64 automatically.
- The `config/config.ini` file controls runtime behavior (`god_mode`, `dry_run`, `vibe_level`). Tests assume default values — avoid committing changes to this file.
- RAM on x86_64 is ~860 MB (PyTorch/CUDA overhead). On ARM Pi Zero 2 W, without PyTorch, it stays under 350 MB.
- The web dashboard (Flask) runs in a daemon thread and auto-polls every 3 seconds; no restart needed for config changes.
