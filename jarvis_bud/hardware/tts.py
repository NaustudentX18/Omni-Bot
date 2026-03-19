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
        self.espeak_bin = shutil.which("espeak-ng") or shutil.which("espeak")

    @property
    def backend(self) -> str:
        if self.piper_bin:
            return "piper"
        if self.espeak_bin:
            return "espeak"
        return "none"

    def speak(self, text: str) -> bool:
        message = text.strip()
        if not message:
            return False
        if self.piper_bin:
            try:
                cmd = (
                    f'printf "%s" "{message.replace(chr(34), "")}" '
                    f'| "{self.piper_bin}" --model "{self.piper_model}" --output-raw '
                    "| aplay -q -r 22050 -f S16_LE -t raw -"
                )
                subprocess.run(cmd, shell=True, check=False, timeout=20)
                return True
            except Exception:
                pass
        if self.espeak_bin:
            try:
                subprocess.run([self.espeak_bin, message], check=False, timeout=20)
                return True
            except Exception:
                return False
        return False
