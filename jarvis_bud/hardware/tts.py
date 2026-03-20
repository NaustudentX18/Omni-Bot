"""Offline text-to-speech abstraction with Piper->espeak fallback."""

from __future__ import annotations

import shutil
import subprocess
from typing import Optional


class SpeechSynth:
    """Tiny TTS shim that keeps runtime resilient on minimal Pi images."""

    def __init__(self, piper_model: str = "models/piper/en_US-lessac-medium.onnx"):
        self.piper_model = piper_model
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

    def speak(self, text: str) -> bool:
        message = text.strip()
        if not message:
            return False
        if self.piper_bin and self.aplay_bin:
            try:
                piper_proc = subprocess.Popen(
                    [self.piper_bin, "--model", self.piper_model, "--output-raw"],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                )
                aplay_proc = subprocess.Popen(
                    [self.aplay_bin, "-q", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-"],
                    stdin=piper_proc.stdout,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if piper_proc.stdout:
                    piper_proc.stdout.close()
                piper_proc.communicate(input=message.encode("utf-8"), timeout=20)
                aplay_proc.wait(timeout=20)
                return piper_proc.returncode == 0 and aplay_proc.returncode == 0
            except Exception:
                pass
        if self.espeak_bin:
            try:
                subprocess.run([self.espeak_bin, message], check=False, timeout=20)
                return True
            except Exception:
                return False
        return False
