"""Lightweight memory layer with optional FAISS + MiniLM backend.

The design keeps the default runtime lean:
- If FAISS and sentence-transformers are available, use vector retrieval.
- Otherwise fallback to JSONL + token-overlap scoring (zero heavy deps).
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class MemoryItem:
    text: str
    meta: dict


class TinyMemory:
    """Small persistent memory optimized for constrained edge devices."""

    def __init__(self, path: str = "logs/memory.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._items: list[MemoryItem] = self._load_items()
        self._faiss: Any = None
        self._encoder: Any = None
        self._vectors: Any = None
        self._enable_vector_backend()

    def _load_items(self) -> list[MemoryItem]:
        items: list[MemoryItem] = []
        if not self.path.exists():
            return items
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    obj = json.loads(line)
                    items.append(MemoryItem(text=obj.get("text", ""), meta=obj.get("meta", {})))
        except Exception:
            return items
        return items

    def _enable_vector_backend(self) -> None:
        if os.environ.get("NXTGENAI_ENABLE_VECTOR_MEMORY", "").lower() not in {"1", "true", "yes"}:
            # Keep memory footprint low by default on Pi Zero class hardware.
            self._faiss = None
            self._encoder = None
            self._vectors = None
            return
        try:
            import faiss  # type: ignore
            import numpy as np  # type: ignore
            from sentence_transformers import SentenceTransformer  # type: ignore

            self._faiss = faiss
            self._encoder = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
            if self._items:
                matrix = self._encoder.encode(
                    [it.text for it in self._items], normalize_embeddings=True
                )
                matrix = np.asarray(matrix, dtype="float32")
                self._vectors = faiss.IndexFlatIP(matrix.shape[1])
                self._vectors.add(matrix)
        except Exception:
            self._faiss = None
            self._encoder = None
            self._vectors = None

    def _append(self, item: MemoryItem) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(
                json.dumps({"text": item.text, "meta": item.meta}, ensure_ascii=True) + "\n"
            )

    def add(self, text: str, meta: dict | None = None) -> None:
        item = MemoryItem(text=text.strip(), meta=meta or {})
        if not item.text:
            return
        self._items.append(item)
        self._append(item)
        if self._encoder and self._faiss:
            try:
                import numpy as np  # type: ignore

                vec = self._encoder.encode([item.text], normalize_embeddings=True)
                vec = np.asarray(vec, dtype="float32")
                if self._vectors is None:
                    self._vectors = self._faiss.IndexFlatIP(vec.shape[1])
                self._vectors.add(vec)
            except Exception:
                pass

    def retrieve(self, query: str, k: int = 3) -> list[MemoryItem]:
        if not self._items:
            return []
        if self._encoder and self._vectors is not None:
            try:
                import numpy as np  # type: ignore

                q = self._encoder.encode([query], normalize_embeddings=True)
                q = np.asarray(q, dtype="float32")
                _, idxs = self._vectors.search(q, min(k, len(self._items)))
                return [self._items[i] for i in idxs[0] if 0 <= i < len(self._items)]
            except Exception:
                pass
        return self._retrieve_token_overlap(query=query, k=k)

    def _retrieve_token_overlap(self, query: str, k: int) -> list[MemoryItem]:
        tokens = set(re.findall(r"[a-zA-Z0-9_]+", query.lower()))
        scored: list[tuple[float, MemoryItem]] = []
        for item in self._items:
            item_tokens = set(re.findall(r"[a-zA-Z0-9_]+", item.text.lower()))
            if not item_tokens:
                continue
            inter = len(tokens & item_tokens)
            if inter == 0:
                continue
            score = inter / math.sqrt(len(item_tokens))
            scored.append((score, item))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [item for _, item in scored[:k]]
