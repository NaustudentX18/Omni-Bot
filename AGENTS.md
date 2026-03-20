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

All 12 tests run without hardware. Be aware that some tests (`test_full_auto_reports_hostname_target_error_cleanly`) depend on `config/config.ini` having `god_mode = false`. If a prior demo or test mutated that file, reset it with `git checkout config/config.ini` before re-running tests.

### Linting

```bash
ruff check .
black --check .
mypy jarvis_bud/ nxtgenai/
bandit -r jarvis_bud/ nxtgenai/ -c pyproject.toml
```

Pre-existing lint/type warnings exist in the codebase (ruff, mypy, black formatting). These are not regressions.

### Running the application

The full `python main.py` requires Raspberry Pi hardware (fails at `initialize_hardware()`). On x86_64 use:

- **Export mode:** `python main.py export` — generates an HTML report + encrypted ZIP without hardware.
- **Module-level testing:** Import `JarvisBud` and call `_execute_voice_intent()` directly to exercise voice command flows, audit logging, AI stack, and tool runner in dry-run mode.

### Key gotchas

- `llama-cpp-python` builds from source during `pip install` — requires `build-essential` and `python3-dev` system packages.
- `sentence-transformers` and `torch` are large downloads (~2 GB total); installs may take several minutes.
- RPi-only dependencies (`RPi.GPIO`, `pyalsaaudio`, `pyaudio`) are platform-gated in `requirements.txt` and skipped on x86_64 automatically.
- The `config/config.ini` file controls runtime behavior (`god_mode`, `dry_run`, `vibe_level`). Tests assume default values — avoid committing changes to this file.
