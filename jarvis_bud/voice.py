"""Voice command parsing and intent normalization."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class VoiceIntent:
    command: str
    args: dict[str, str]
    risk: int


class VoiceCommandParser:
    """Keyword parser tuned for low-resource offline command routing."""

    def parse(self, text: str) -> VoiceIntent | None:
        normalized = " ".join(text.lower().strip().split())
        if not normalized:
            return None

        if "make legendary" in normalized:
            return VoiceIntent(command="make_legendary", args={}, risk=2)
        if "god mode" in normalized:
            return VoiceIntent(command="god_mode", args={}, risk=1)
        if "full auto" in normalized:
            return VoiceIntent(command="full_auto", args={}, risk=6)
        if normalized.startswith("status"):
            return VoiceIntent(command="status", args={}, risk=1)
        if normalized.startswith("stop"):
            return VoiceIntent(command="stop", args={}, risk=1)
        if normalized.startswith("export"):
            return VoiceIntent(command="export", args={}, risk=2)
        if "crack wifi" in normalized:
            return VoiceIntent(command="crack_wifi", args={}, risk=8)
        if "sync now" in normalized or "sync peers" in normalized:
            return VoiceIntent(command="sync_now", args={}, risk=2)

        target_match = re.search(r"target add\s+([a-zA-Z0-9.\-/:_]+)", normalized)
        if target_match:
            return VoiceIntent(command="target_add", args={"target": target_match.group(1)}, risk=2)

        return VoiceIntent(command="chat", args={"text": text.strip()}, risk=1)
