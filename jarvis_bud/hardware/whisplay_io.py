"""Whisplay HAT device facade for display, audio codec, and buttons."""

from __future__ import annotations

import asyncio
from typing import Callable, Optional

from jarvis_bud.hardware.audio import AudioCodec
from jarvis_bud.hardware.buttons import ButtonHandler
from jarvis_bud.hardware.lcd import ST7789Display


class WhisplayIO:
    """Driver-level orchestration for ST7789 + WM8960 + GPIO buttons."""

    def __init__(self):
        self.display = ST7789Display()
        self.audio = AudioCodec()
        self.buttons = ButtonHandler()
        self.initialized = False

    def initialize(self) -> bool:
        display_ok = self.display.init()
        audio_ok = self.audio.init()
        self.initialized = bool(display_ok)
        if not audio_ok:
            print("⚠️ WM8960 audio unavailable; continuing without mic capture.")
        return self.initialized

    def set_callbacks(
        self,
        on_button_a: Optional[Callable[[], None]] = None,
        on_button_b: Optional[Callable[[], None]] = None,
        on_button_b_long_press: Optional[Callable[[], None]] = None,
    ):
        if on_button_a:
            self.buttons.on_button_a(on_button_a)
        if on_button_b:
            self.buttons.on_button_b(on_button_b)
        if on_button_b_long_press:
            self.buttons.on_button_b_long_press(on_button_b_long_press)

    async def capture_audio(self, seconds: float = 4.0) -> bytes:
        """Capture microphone audio into raw bytes."""
        if not self.audio.is_initialized:
            return b""

        chunks = []
        loops = int(max(1, (self.audio.sample_rate / self.audio.chunk_size) * seconds))
        self.audio.start_recording()
        for _ in range(loops):
            data = self.audio.capture_chunk()
            if data:
                chunks.append(data)
            await asyncio.sleep(0.01)
        self.audio.stop_recording()
        return b"".join(chunks)

    def cleanup(self):
        self.buttons.cleanup()
        self.audio.cleanup()
