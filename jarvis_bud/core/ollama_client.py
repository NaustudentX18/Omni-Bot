"""Local Ollama integration with low-latency host discovery for Pi networks."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

import requests


@dataclass
class OllamaEndpoint:
    """Resolved Ollama endpoint details."""

    host: str
    port: int
    latency_ms: float

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


class LocalOllamaClient:
    """Talk to local Ollama and auto-discover fast LAN hosts."""

    PREFERRED_MODEL_PREFIXES = ("llama3", "mistral")

    def __init__(
        self,
        candidate_hosts: Optional[Iterable[str]] = None,
        port: int = 11434,
        max_ping_ms: float = 100.0,
        request_timeout: float = 8.0,
    ):
        self.port = port
        self.max_ping_ms = max_ping_ms
        self.request_timeout = request_timeout
        self.candidate_hosts = list(
            candidate_hosts
            or [
                "127.0.0.1",
                "localhost",
                "192.168.1.100",
                "192.168.1.101",
                "192.168.1.110",
                "pironman",
                "naspi",
            ]
        )
        self.endpoint: Optional[OllamaEndpoint] = None
        self.model: Optional[str] = None

    @staticmethod
    def _extract_ping_ms(output: str) -> Optional[float]:
        match = re.search(r"time[=<]([0-9.]+)\\s*ms", output)
        if not match:
            return None
        try:
            return float(match.group(1))
        except ValueError:
            return None

    def ping_host(self, host: str) -> Optional[float]:
        """Return one-way ping roundtrip in ms if reachable."""
        try:
            proc = subprocess.run(
                ["ping", "-c", "1", "-W", "1", host],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            if proc.returncode != 0:
                return None
            return self._extract_ping_ms(proc.stdout)
        except Exception:
            return None

    def _is_ollama_alive(self, base_url: str) -> bool:
        try:
            response = requests.get(f"{base_url}/api/tags", timeout=self.request_timeout)
            return response.status_code == 200
        except Exception:
            return False

    def scan(self) -> Optional[OllamaEndpoint]:
        """Find the first responsive Ollama endpoint under latency target."""
        best: Optional[Tuple[float, str]] = None

        for host in self.candidate_hosts:
            latency = self.ping_host(host)
            if latency is None or latency > self.max_ping_ms:
                continue
            if best is None or latency < best[0]:
                best = (latency, host)

        if best is None:
            self.endpoint = None
            return None

        latency_ms, host = best
        endpoint = OllamaEndpoint(host=host, port=self.port, latency_ms=latency_ms)

        if self._is_ollama_alive(endpoint.base_url):
            self.endpoint = endpoint
            self.model = self.detect_preferred_model()
            return endpoint

        self.endpoint = None
        return None

    def list_models(self) -> List[str]:
        if not self.endpoint:
            return []
        try:
            response = requests.get(
                f"{self.endpoint.base_url}/api/tags",
                timeout=self.request_timeout,
            )
            response.raise_for_status()
            models = response.json().get("models", [])
            return [m.get("name", "") for m in models if m.get("name")]
        except Exception:
            return []

    def detect_preferred_model(self) -> Optional[str]:
        models = self.list_models()
        for prefix in self.PREFERRED_MODEL_PREFIXES:
            for model in models:
                if model.lower().startswith(prefix):
                    return model
        return models[0] if models else None

    @property
    def is_available(self) -> bool:
        return self.endpoint is not None

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[str]:
        """Generate text with local Ollama endpoint."""
        if not self.endpoint:
            return None

        payload = {
            "model": self.model or "llama3",
            "prompt": prompt,
            "stream": False,
            "temperature": 0.7,
            "top_p": 0.9,
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            response = requests.post(
                f"{self.endpoint.base_url}/api/generate",
                json=payload,
                timeout=self.request_timeout,
            )
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except Exception:
            return None
