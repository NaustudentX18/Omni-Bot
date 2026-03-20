"""Offline Speech-to-Text using faster-whisper (tiny model, Pi Zero 2 W safe).

Downloads the tiny model on first use (~75 MB). Runs inference on CPU with
int8 quantization to stay under 80 MB resident. Falls back to a no-op
transcriber if faster-whisper is not installed.
"""

from __future__ import annotations

import io
import os
import struct
import tempfile
import time
import wave
from pathlib import Path
from typing import Optional


class SpeechToText:
    """Offline STT engine using faster-whisper tiny model."""

    MODEL_SIZE = "tiny"
    COMPUTE_TYPE = "int8"

    def __init__(
        self,
        model_dir: str = "models/whisper",
        language: str = "en",
        beam_size: int = 1,
    ):
        self.model_dir = model_dir
        self.language = language
        self.beam_size = beam_size
        self._model = None
        self._available = False
        self._load_model()

    def _load_model(self) -> None:
        try:
            from faster_whisper import WhisperModel  # type: ignore[import-untyped]
        except ImportError:
            print("⚠️  faster-whisper not installed; STT disabled.")
            return

        os.makedirs(self.model_dir, exist_ok=True)
        try:
            self._model = WhisperModel(
                self.MODEL_SIZE,
                device="cpu",
                compute_type=self.COMPUTE_TYPE,
                download_root=self.model_dir,
                cpu_threads=2,
            )
            self._available = True
            print(f"🎙️  STT model loaded: whisper-{self.MODEL_SIZE} ({self.COMPUTE_TYPE})")
        except Exception as exc:
            print(f"⚠️  STT model load failed: {exc}")
            self._model = None

    @property
    def is_available(self) -> bool:
        return self._available and self._model is not None

    def transcribe_bytes(
        self,
        audio_bytes: bytes,
        sample_rate: int = 16000,
        channels: int = 1,
        sample_width: int = 2,
    ) -> str:
        """Transcribe raw PCM audio bytes to text.

        Args:
            audio_bytes: Raw 16-bit PCM audio data
            sample_rate: Sample rate in Hz
            channels: Number of audio channels
            sample_width: Bytes per sample (2 = 16-bit)

        Returns:
            Transcribed text or empty string on failure
        """
        if not self.is_available or not audio_bytes:
            return ""

        wav_path: Optional[str] = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                wav_path = tmp.name
                with wave.open(tmp, "wb") as wf:
                    wf.setnchannels(channels)
                    wf.setsampwidth(sample_width)
                    wf.setframerate(sample_rate)
                    wf.writeframes(audio_bytes)

            segments, info = self._model.transcribe(
                wav_path,
                language=self.language,
                beam_size=self.beam_size,
                vad_filter=True,
                vad_parameters=dict(min_silence_duration_ms=500),
            )
            text = " ".join(seg.text.strip() for seg in segments).strip()
            return text
        except Exception as exc:
            print(f"⚠️  STT transcription error: {exc}")
            return ""
        finally:
            if wav_path and os.path.exists(wav_path):
                os.unlink(wav_path)

    def transcribe_file(self, wav_path: str) -> str:
        """Transcribe a WAV file to text."""
        if not self.is_available:
            return ""
        try:
            segments, _ = self._model.transcribe(
                wav_path,
                language=self.language,
                beam_size=self.beam_size,
                vad_filter=True,
            )
            return " ".join(seg.text.strip() for seg in segments).strip()
        except Exception as exc:
            print(f"⚠️  STT file transcription error: {exc}")
            return ""

    def estimate_ram_mb(self) -> float:
        """Estimate current RAM usage of the model."""
        if not self.is_available:
            return 0.0
        try:
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF)
            return usage.ru_maxrss / 1024.0
        except Exception:
            return 75.0
