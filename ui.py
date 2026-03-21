"""Top-level deployment UI helpers for emergency and risk confirmations."""

from __future__ import annotations

import time


def button_confirm(buttons, timeout_s: float = 6.0) -> bool:
    """Wait for Button A press confirmation inside a bounded timeout."""
    if not buttons:
        return False
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            if buttons.get_button_a_state():
                return True
        except Exception:
            return False
        time.sleep(0.05)
    return False


def emergency_banner_text(reason: str | None = None) -> str:
    suffix = f" // {reason}" if reason else ""
    return f"EMERGENCY STOP ENGAGED{suffix}"
