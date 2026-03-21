"""Tamper-evident audit logging for offline Raspberry Pi deployments.

This module provides a write-once style JSONL ledger where each event is
cryptographically chained to the previous event using SHA-256. The chain makes
silent editing of historical records detectable during verification.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

GENESIS_HASH = "0" * 64


@dataclass(frozen=True)
class AuditRecord:
    """Single audit entry emitted into the chained ledger."""

    ts: float
    event: str
    payload: dict[str, Any]
    prev_hash: str
    hash: str

    def to_json(self) -> str:
        return json.dumps(
            {
                "ts": self.ts,
                "event": self.event,
                "payload": self.payload,
                "prev_hash": self.prev_hash,
                "hash": self.hash,
            },
            sort_keys=True,
            ensure_ascii=True,
        )


class AuditLogger:
    """Append-only, SHA-256 chained audit log.

    Design intent:
    - Never rewrite old records; only append.
    - Hash each event over canonical JSON + previous hash.
    - Verify chain integrity quickly during startup or export.
    """

    def __init__(self, path: str = "logs/audit_chain.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._last_hash = self._read_last_hash()

    def _read_last_hash(self) -> str:
        if not self.path.exists():
            return GENESIS_HASH
        last_line = ""
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if line.strip():
                        last_line = line.strip()
        except OSError:
            return GENESIS_HASH
        if not last_line:
            return GENESIS_HASH
        try:
            payload = json.loads(last_line)
            candidate = payload.get("hash", "")
            if isinstance(candidate, str) and len(candidate) == 64:
                return candidate
        except json.JSONDecodeError:
            return GENESIS_HASH
        return GENESIS_HASH

    @staticmethod
    def _canonical_payload(event: str, payload: dict[str, Any], ts: float, prev_hash: str) -> str:
        return json.dumps(
            {"event": event, "payload": payload, "prev_hash": prev_hash, "ts": ts},
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
        )

    def log_event(self, event: str, payload: dict[str, Any] | None = None) -> AuditRecord:
        """Append an event into the hash chain and fsync to disk."""
        payload = payload or {}
        ts = time.time()
        with self._lock:
            prev_hash = self._last_hash
            canonical = self._canonical_payload(
                event=event, payload=payload, ts=ts, prev_hash=prev_hash
            )
            record_hash = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
            record = AuditRecord(
                ts=ts, event=event, payload=payload, prev_hash=prev_hash, hash=record_hash
            )

            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(record.to_json() + "\n")
                handle.flush()
                os.fsync(handle.fileno())

            self._last_hash = record_hash
            return record

    def verify_chain(self) -> bool:
        """Verify every link in the audit chain."""
        if not self.path.exists():
            return True
        previous = GENESIS_HASH
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    event = json.loads(line)
                    ts = event["ts"]
                    name = event["event"]
                    payload = event.get("payload", {})
                    prev_hash = event["prev_hash"]
                    chain_hash = event["hash"]
                    if prev_hash != previous:
                        return False
                    canonical = self._canonical_payload(
                        event=name,
                        payload=payload,
                        ts=ts,
                        prev_hash=prev_hash,
                    )
                    calculated = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
                    if calculated != chain_hash:
                        return False
                    previous = chain_hash
        except (OSError, KeyError, json.JSONDecodeError, TypeError):
            return False
        return True
