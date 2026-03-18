"""Personality system for Omni-Bot with emoji text enhancements."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

from jarvis_bud.ai.openrouter_client import OpenRouterClient
from jarvis_bud.core.ollama_client import LocalOllamaClient


@dataclass
class BudProfile:
    """A single personality profile."""

    bud_id: str
    name: str
    emoji: str
    role: str
    tone: str
    specialty: str
    style: str
    system_prompt: str


class EmojiTextEngine:
    """Replaces key words with technical emojis."""

    MAPPING = {
        "code": "💻",
        "coding": "💻",
        "python": "🐍",
        "docker": "🐳",
        "print": "🖨️",
        "printing": "🖨️",
        "success": "✅",
        "error": "⚠️",
        "idea": "💡",
    }

    @classmethod
    def apply(cls, text: str) -> str:
        updated = text
        for key, emoji in cls.MAPPING.items():
            updated = updated.replace(key, f"{emoji} {key}")
            updated = updated.replace(key.capitalize(), f"{emoji} {key.capitalize()}")
        return updated


class BudManager:
    """Manage active personality and route inference between local/cloud."""

    def __init__(
        self,
        ollama: LocalOllamaClient,
        openrouter_key: Optional[str] = None,
    ):
        self.ollama = ollama
        self.openrouter = OpenRouterClient(api_key=openrouter_key) if openrouter_key else None
        self.buds: Dict[str, BudProfile] = self._build_buds()
        self.active_bud_id = "fogo"

    def _build_buds(self) -> Dict[str, BudProfile]:
        return {
            "fogo": BudProfile(
                bud_id="fogo",
                name="Fogo",
                emoji="🐐💻",
                role="Python, Docker, and 3D printing specialist",
                tone="Creative, proactive, hacker-ready",
                specialty="Project brainstorming for maker builds and uConsole ideas",
                style="Punchy technical tips with emoji accents",
                system_prompt=(
                    "You are Fogo, an elite maker-side AI in a Pi Zero 2 W build. "
                    "You are an expert in Python, Docker, and 3D printing with "
                    "Bambu Lab P1S and OrcaSlicer workflows. "
                    "Tone: highly creative, proactive with ideas, slightly hacker-ready. "
                    "Specialty: brainstorming practical projects quickly. "
                    "Style: use technical emojis naturally and concise, punchy advice. "
                    "Example phrase style: 'Layer height looking a bit thick there, mate! 🖨️✨'"
                ),
            ),
            "mango": BudProfile(
                bud_id="mango",
                name="Mango",
                emoji="🥭",
                role="Peace, love, and vibe-focused companion",
                tone="Calm, kind, grounding",
                specialty="Motivation, reflection, and balanced planning",
                style="Warm and mellow with practical optimism",
                system_prompt=(
                    "You are Mango, a peaceful and uplifting AI companion focused on "
                    "clarity, emotional balance, and thoughtful plans. Keep answers gentle, "
                    "use friendly emoji lightly, and help users make progress without overwhelm."
                ),
            ),
        }

    def set_active_bud(self, bud_id: str) -> bool:
        if bud_id not in self.buds:
            return False
        self.active_bud_id = bud_id
        return True

    def cycle_bud(self) -> BudProfile:
        keys = list(self.buds.keys())
        idx = keys.index(self.active_bud_id)
        self.active_bud_id = keys[(idx + 1) % len(keys)]
        return self.active_profile

    @property
    def active_profile(self) -> BudProfile:
        return self.buds[self.active_bud_id]

    def active_icon(self, user_text: str = "") -> str:
        if self.active_bud_id != "fogo":
            return "✨"
        text = user_text.lower()
        if any(k in text for k in ["print", "orca", "bambu", "slicer", "stl"]):
            return "🖨️"
        return "💻"

    def generate_response(self, user_prompt: str) -> str:
        """Generate response with local-first, cloud failover behavior."""
        profile = self.active_profile
        prompt = f"User request: {user_prompt}"

        if self.ollama.scan():
            reply = self.ollama.generate(prompt=prompt, system_prompt=profile.system_prompt)
            if reply:
                return EmojiTextEngine.apply(reply)

        if self.openrouter and self.openrouter.is_available:
            reply = self.openrouter.generate(prompt=prompt, system_prompt=profile.system_prompt)
            if reply:
                return EmojiTextEngine.apply(reply)

        fallback = "No AI route right now. Ollama is offline and cloud fallback is unavailable."
        return EmojiTextEngine.apply(fallback)
