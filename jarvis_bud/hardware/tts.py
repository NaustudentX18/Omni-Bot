"""Offline text-to-speech abstraction with Piper->espeak fallback."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class SpeechSynth:
    """Tiny TTS shim that keeps runtime resilient on minimal Pi images."""

    def __init__(self, piper_model: str = "models/piper/en_US-lessac-medium.onnx", profile: str = "standard"):
        self.piper_model = self._resolve_model(piper_model)
        self.profile = profile
        self.piper_bin = shutil.which("piper")
        self.aplay_bin = shutil.which("aplay")
        self.espeak_bin = shutil.which("espeak-ng") or shutil.which("espeak")
        self._profile_settings = {
            "cyberpunk": {"length_scale": 0.92, "noise_scale": 0.74, "noise_w": 0.86, "espeak_rate": 165, "espeak_pitch": 52},
            "calm": {"length_scale": 1.0, "noise_scale": 0.67, "noise_w": 0.8, "espeak_rate": 145, "espeak_pitch": 44},
            "standard": {"length_scale": 1.0, "noise_scale": 0.7, "noise_w": 0.8, "espeak_rate": 155, "espeak_pitch": 48},
        }

    def _resolve_model(self, requested_model: str) -> str:
        if Path(requested_model).exists():
            return requested_model
        fallback = Path("models/piper/en_US-lessac-medium.onnx")
        if fallback.exists():
            return str(fallback)
        return requested_model

    def set_profile(self, profile: str) -> None:
        if profile in self._profile_settings:
            self.profile = profile

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
                profile = self._profile_settings.get(self.profile, self._profile_settings["standard"])
                piper_cmd = [self.piper_bin, "--model", self.piper_model, "--output-raw"]
                if self.profile != "standard":
                    piper_cmd.extend(
                        [
                            "--length_scale",
                            str(profile["length_scale"]),
                            "--noise_scale",
                            str(profile["noise_scale"]),
                            "--noise_w",
                            str(profile["noise_w"]),
                        ]
                    )
                piper_proc = subprocess.Popen(
                    piper_cmd,
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
                if piper_proc.stdin:
                    piper_proc.stdin.write(message.encode("utf-8"))
                    piper_proc.stdin.close()
                piper_proc.wait(timeout=20)
                if piper_proc.stdout:
                    piper_proc.stdout.close()
                aplay_proc.wait(timeout=20)
                return piper_proc.returncode == 0 and aplay_proc.returncode == 0
            except Exception:
                pass
        if self.espeak_bin:
            try:
                profile = self._profile_settings.get(self.profile, self._profile_settings["standard"])
                subprocess.run(
                    [
                        self.espeak_bin,
                        "-s",
                        str(profile["espeak_rate"]),
                        "-p",
                        str(profile["espeak_pitch"]),
                        message,
                    ],
                    check=False,
                    timeout=20,
                )
                return True
            except Exception:
                return False
        return False
