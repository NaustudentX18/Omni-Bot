"""Constrained offline AI brain with planning + reflection stages."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jarvis_bud.ai.memory import TinyMemory
from jarvis_bud.ai.prompts import build_system_prompt
from jarvis_bud.audit import AuditLogger


class EdgeBrain:
    """Offline-first brain that tries GGUF models with deterministic fallbacks."""

    MODEL_CANDIDATES = [
        "models/gemma-2-2b-it-Q4_K_M.gguf",
        "models/phi-3.5-mini-instruct-Q4_K_M.gguf",
        "models/tinyllama-1.1b-chat-v1.0-Q4_K_M.gguf",
    ]

    def __init__(
        self,
        audit: AuditLogger,
        memory_path: str = "logs/memory.jsonl",
        vibe_level: str = "cinematic",
    ):
        self.audit = audit
        self.memory = TinyMemory(memory_path)
        self.vibe_level = vibe_level
        self._llm: Any = None
        self._model_path: str | None = None
        self._load_llm()

    def _load_llm(self) -> None:
        try:
            from llama_cpp import Llama  # type: ignore
        except Exception:
            self._llm = None
            self._model_path = None
            return

        for model in self.MODEL_CANDIDATES:
            if not Path(model).exists():
                continue
            try:
                self._llm = Llama(
                    model_path=model,
                    n_ctx=2048,
                    n_gpu_layers=0,
                    n_threads=2,
                    logits_all=False,
                    verbose=False,
                )
                self._model_path = model
                self.audit.log_event("brain.model_loaded", {"model_path": model})
                return
            except Exception:
                continue
        self._llm = None
        self._model_path = None

    @staticmethod
    def score_risk(text: str) -> int:
        text_l = text.lower()
        score = 1
        high = ("deauth", "spoof", "hydra", "sqlmap", "exploit", "arp", "crack wifi")
        medium = ("scan", "recon", "enumerate", "nikto", "gobuster")
        if any(token in text_l for token in medium):
            score = max(score, 4)
        if any(token in text_l for token in high):
            score = max(score, 7)
        return min(score, 10)

    def _build_prompt(self, user_prompt: str, memory_context: list[str]) -> str:
        payload = {
            "system": build_system_prompt(vibe_level=self.vibe_level),
            "memory": memory_context,
            "user": user_prompt,
            "format": {
                "plan": "list",
                "action": "string",
                "reflection": "string",
                "final": "string",
            },
        }
        return json.dumps(payload, ensure_ascii=True)

    def _infer(self, text: str) -> str:
        if self._llm is None:
            # Deterministic no-LLM fallback still follows planning/reflection protocol.
            return (
                '{"plan":["Assess request safely","Use available offline tools","Confirm risky operations"],'
                '"action":"Proceed in dry-run if risk >= 6 until confirmed.",'
                '"reflection":"No local GGUF runtime loaded; fallback response path used.",'
                '"final":"Offline fallback: request received and queued with safety controls."}'
            )
        output = self._llm(text, max_tokens=320, temperature=0.4, top_p=0.9, stop=["</s>"])
        if not output or "choices" not in output:
            return "{}"
        return output["choices"][0]["text"].strip()

    def respond(self, user_prompt: str) -> dict[str, object]:
        risk = self.score_risk(user_prompt)
        memory = [item.text for item in self.memory.retrieve(user_prompt, k=3)]
        prompt = self._build_prompt(user_prompt=user_prompt, memory_context=memory)
        raw = self._infer(prompt)
        self.audit.log_event(
            "brain.decision",
            {
                "prompt_preview": user_prompt[:160],
                "risk": risk,
                "model_path": self._model_path,
                "memory_hits": len(memory),
            },
        )

        # Best-effort parse of structured JSON. Fallback to plain text.
        parsed: dict[str, object]
        try:
            candidate = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
            parsed = json.loads(candidate)
        except Exception:
            parsed = {
                "plan": ["Evaluate request", "Apply safety checks", "Return concise response"],
                "action": "Generated from fallback parser",
                "reflection": "Model output was not strict JSON; converted safely.",
                "final": raw[:1200] if raw else "No output generated.",
            }

        parsed["risk"] = risk
        self.memory.add(f"Q: {user_prompt}\nA: {parsed.get('final', '')}", {"risk": risk})
        return parsed
