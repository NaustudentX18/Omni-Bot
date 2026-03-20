"""STT regression tests for offline fallback behavior."""

from __future__ import annotations

import os

from jarvis_bud.hardware.stt import SpeechToTextEngine


def test_stt_env_override_wins():
    engine = SpeechToTextEngine()
    os.environ["NXTGENAI_FAKE_STT"] = "status"
    try:
        result = engine.transcribe(b"fake")
    finally:
        os.environ.pop("NXTGENAI_FAKE_STT", None)
    assert result.text == "status"
    assert result.backend == "env"


def test_stt_empty_audio_returns_empty():
    engine = SpeechToTextEngine()
    result = engine.transcribe(b"")
    assert result.text == ""
    assert result.backend == "none"
