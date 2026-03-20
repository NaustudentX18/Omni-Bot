"""Offline text-to-speech with Piper (cyberpunk voice) -> espeak-ng fallback.

Piper voices:
  - en_US-lessac-medium (default, clean voice)
  - en_GB-alan-medium   (British, deeper)

The caller can override rate and pitch for cyberpunk flavor.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from typing import Optional


class SpeechSynth:
    """Multi-backend TTS: Piper (preferred) -> espeak-ng -> silent."""

    PIPER_VOICES = {
        "cyberpunk": "models/piper/en_US-lessac-medium.onnx",
        "default": "models/piper/en_US-lessac-medium.onnx",
        "british": "models/piper/en_GB-alan-medium.onnx",
    }

    def __init__(
        self,
        piper_model: str = "models/piper/en_US-lessac-medium.onnx",
        voice_style: str = "cyberpunk",
        speaking_rate: float = 1.0,
        pitch_semitones: int = 0,
    ):
        self.voice_style = voice_style
        self.piper_model = self.PIPER_VOICES.get(voice_style, piper_model)
        self.speaking_rate = max(0.5, min(2.0, speaking_rate))
        self.pitch_semitones = max(-12, min(12, pitch_semitones))
        self.piper_bin = shutil.which("piper")
        self.aplay_bin = shutil.which("aplay")
        self.espeak_bin = shutil.which("espeak-ng") or shutil.which("espeak")

    @property
    def backend(self) -> str:
        if self.piper_bin and self.aplay_bin:
            return "piper"
        if self.espeak_bin:
            return "espeak"
        return "none"

    def set_voice(self, style: str) -> None:
        """Switch voice style at runtime."""
        if style in self.PIPER_VOICES:
            self.voice_style = style
            self.piper_model = self.PIPER_VOICES[style]

    def speak(self, text: str) -> bool:
        """Speak text using the best available TTS backend."""
        message = text.strip()
        if not message:
            return False

        if self.piper_bin and self.aplay_bin:
            return self._speak_piper(message)

        if self.espeak_bin:
            return self._speak_espeak(message)

        return False

    def speak_to_file(self, text: str, output_path: str) -> bool:
        """Synthesize speech and save to a WAV file instead of playing."""
        message = text.strip()
        if not message:
            return False

        if self.piper_bin:
            try:
                result = subprocess.run(
                    [
                        self.piper_bin,
                        "--model", self.piper_model,
                        "--output_file", output_path,
                    ],
                    input=message.encode("utf-8"),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=30,
                )
                return result.returncode == 0
            except Exception:
                return False

        if self.espeak_bin:
            try:
                result = subprocess.run(
                    [self.espeak_bin, "-w", output_path, message],
                    check=False,
                    timeout=20,
                )
                return result.returncode == 0
            except Exception:
                return False

        return False

    def _speak_piper(self, message: str) -> bool:
        """Speak using Piper TTS piped into aplay."""
        try:
            piper_cmd = [self.piper_bin, "--model", self.piper_model, "--output-raw"]
            if self.speaking_rate != 1.0:
                piper_cmd.extend(["--length-scale", str(round(1.0 / self.speaking_rate, 2))])

            piper_proc = subprocess.Popen(
                piper_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )

            sample_rate = str(int(22050 * self.speaking_rate)) if self.speaking_rate != 1.0 else "22050"
            aplay_proc = subprocess.Popen(
                [self.aplay_bin, "-q", "-r", sample_rate, "-f", "S16_LE", "-t", "raw", "-"],
                stdin=piper_proc.stdout,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            if piper_proc.stdin:
                piper_proc.stdin.write(message.encode("utf-8"))
                piper_proc.stdin.close()
            piper_proc.wait(timeout=20)
            if piper_proc.stdout:
                piper_proc.stdout.close()
            aplay_proc.wait(timeout=20)
            return piper_proc.returncode == 0 and aplay_proc.returncode == 0
        except Exception:
            return False

    def _speak_espeak(self, message: str) -> bool:
        """Speak using espeak-ng as fallback."""
        try:
            cmd = [self.espeak_bin]
            if self.pitch_semitones != 0:
                espeak_pitch = max(0, min(99, 50 + self.pitch_semitones * 4))
                cmd.extend(["-p", str(espeak_pitch)])
            if self.speaking_rate != 1.0:
                wpm = int(175 * self.speaking_rate)
                cmd.extend(["-s", str(wpm)])
            cmd.append(message)
            subprocess.run(cmd, check=False, timeout=20)
            return True
        except Exception:
            return False
