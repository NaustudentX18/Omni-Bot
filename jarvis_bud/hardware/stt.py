"""Offline speech-to-text engine with faster-whisper and whisper.cpp support."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import time
import wave
from dataclasses import dataclass
from pathlib import Path


@dataclass
class STTResult:
    """Normalized transcription payload."""

    text: str
    backend: str
    latency_ms: float


class SpeechToTextEngine:
    """Pi-safe, offline-first STT with tiny-model defaults."""

    def __init__(
        self,
        model_size: str = "tiny.en",
        model_root: str = "models/whisper",
        sample_rate: int = 16000,
    ):
        self.model_size = model_size
        self.model_root = model_root
        self.sample_rate = sample_rate
        self._fw_model = None
        self._fw_error: str | None = None
        self._whisper_cli = shutil.which("whisper-cli") or shutil.which("whisper")
        self._whisper_cpp_model = self._discover_whisper_cpp_model()

    def _discover_whisper_cpp_model(self) -> str | None:
        model_dir = Path(self.model_root)
        if not model_dir.exists():
            return None
        candidates = [
            model_dir / "ggml-tiny.en.bin",
            model_dir / "ggml-tiny.bin",
            model_dir / "ggml-base.en.bin",
        ]
        for candidate in candidates:
            if candidate.exists():
                return str(candidate)
        return None

    def _load_faster_whisper(self):
        if self._fw_model is not None:
            return self._fw_model
        if self._fw_error:
            return None
        try:
            from faster_whisper import WhisperModel  # type: ignore

            self._fw_model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8",
                download_root=self.model_root,
                local_files_only=bool(int(os.environ.get("NXTGENAI_STT_LOCAL_ONLY", "0"))),
                cpu_threads=max(1, int(os.environ.get("NXTGENAI_STT_THREADS", "2"))),
            )
            return self._fw_model
        except Exception as exc:
            self._fw_error = str(exc)
            return None

    def _write_temp_wav(self, audio_data: bytes) -> str:
        with tempfile.NamedTemporaryFile(
            prefix="nxtgenai_stt_", suffix=".wav", delete=False
        ) as handle:
            path = handle.name
        with wave.open(path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_data)
        return path

    def _transcribe_faster_whisper(self, wav_path: str) -> STTResult | None:
        model = self._load_faster_whisper()
        if model is None:
            return None
        start = time.monotonic()
        segments, _info = model.transcribe(
            wav_path,
            beam_size=1,
            language="en",
            vad_filter=True,
            condition_on_previous_text=False,
        )
        text = " ".join((segment.text or "").strip() for segment in segments).strip()
        elapsed = (time.monotonic() - start) * 1000.0
        if not text:
            return None
        return STTResult(text=text, backend="faster-whisper", latency_ms=elapsed)

    def _transcribe_whisper_cpp(self, wav_path: str) -> STTResult | None:
        if not self._whisper_cli or not self._whisper_cpp_model:
            return None
        start = time.monotonic()
        proc = subprocess.run(
            [
                self._whisper_cli,
                "-m",
                self._whisper_cpp_model,
                "-f",
                wav_path,
                "-l",
                "en",
                "-nt",
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        elapsed = (time.monotonic() - start) * 1000.0
        if proc.returncode != 0:
            return None
        lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
        text = " ".join(line for line in lines if not line.startswith("["))[:500].strip()
        if not text:
            return None
        return STTResult(text=text, backend="whisper.cpp", latency_ms=elapsed)

    def transcribe(self, audio_data: bytes) -> STTResult:
        """Transcribe PCM 16-bit mono audio data."""
        scripted = os.environ.get("NXTGENAI_FAKE_STT", "").strip()
        if scripted:
            return STTResult(text=scripted, backend="env", latency_ms=0.0)
        if not audio_data:
            return STTResult(text="", backend="none", latency_ms=0.0)

        wav_path = self._write_temp_wav(audio_data)
        try:
            fw_result = self._transcribe_faster_whisper(wav_path)
            if fw_result:
                return fw_result
            cpp_result = self._transcribe_whisper_cpp(wav_path)
            if cpp_result:
                return cpp_result
            return STTResult(text="status", backend="fallback", latency_ms=0.0)
        finally:
            try:
                os.unlink(wav_path)
            except OSError:
                pass
