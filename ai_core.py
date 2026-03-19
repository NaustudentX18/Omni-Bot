"""Compatibility AI core with ReAct-like safety loop and risk gating."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from jarvis_bud.ai.brain import EdgeBrain


@dataclass
class AIActionDecision:
    prompt: str
    risk: int
    should_execute: bool
    reasoning: str
    output: Dict[str, object]


class ReActCore:
    """Thin adapter preserving ai_core.py style integration points."""

    def __init__(self, brain: EdgeBrain, max_risk: int = 7):
        self.brain = brain
        self.max_risk = max_risk

    def decide(self, prompt: str) -> AIActionDecision:
        result = self.brain.respond(prompt)
        risk = int(result.get("risk", 1))
        should_execute = risk <= self.max_risk
        reasoning = "risk within threshold" if should_execute else "risk exceeded threshold; skip"
        return AIActionDecision(
            prompt=prompt,
            risk=risk,
            should_execute=should_execute,
            reasoning=reasoning,
            output=result,
        )
