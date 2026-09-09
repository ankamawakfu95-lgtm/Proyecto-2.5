"""Índice curado de notas Markdown para recuperación local y trazable."""
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


class ObsidianMemory:
    def __init__(self, vault_path: str | Path | None = None):
        configured = vault_path or os.getenv("MATEO_OBSIDIAN_VAULT") or os.getenv("OBSIDIAN_VAULT_PATH")
        self.vault_path = Path(configured or Path(__file__).resolve().parents[1] / "obsidian").expanduser().resolve()
        self.documents: List[Dict[str, Any]] = []
        self.initialize_memory()

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"\w+", text.lower(), flags=re.UNICODE))

    def initialize_memory(self) -> int:
        self.documents = []
        if not self.vault_path.exists():
            return 0
        for path in sorted(self.vault_path.rglob("*.md")):
            if any(part.startswith(".") or part.lower() in {"archive", "archived"} for part in path.parts):
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace").strip()
            except OSError:
                continue
            if len(text) < 80 or text.startswith("<!--"):
                continue
            metadata, body = self._parse(text)
            self.documents.append({"path": path, "text": text, "body": body, "metadata": metadata})
        return len(self.documents)

    @staticmethod
    def _parse(text: str) -> tuple[Dict[str, str], str]:
        metadata: Dict[str, str] = {}
        body = text
        if text.startswith("---\n"):
            parts = text.split("---\n", 2)
            if len(parts) == 3:
                for line in parts[1].splitlines():
                    if ":" in line:
                        key, value = line.split(":", 1)
                        metadata[key.strip()] = value.strip().strip("[]")
                body = parts[2]
        return metadata, body

    def search_memory(self, query: str, k: int = 4) -> List[str]:
        terms = self._tokens(str(query))
        if not terms:
            return []
        scored = []
        for item in self.documents:
            body_terms = self._tokens(item["body"])
            title_terms = self._tokens(item["metadata"].get("title", ""))
            score = len(terms & body_terms) + (2 * len(terms & title_terms))
            if score:
                updated = item["metadata"].get("updated", "")
                try:
                    recency = datetime.fromisoformat(updated.replace("Z", "+00:00")).timestamp()
                except ValueError:
                    recency = 0
                scored.append((score, recency, str(item["path"]), item["text"]))
        scored.sort(key=lambda row: (-row[0], -row[1], row[2]))
        return [row[3] for row in scored[:max(0, k)]]

    def get_stats(self) -> dict:
        categories: Dict[str, int] = {}
        for item in self.documents:
            category = item["metadata"].get("category", "uncategorized")
            categories[category] = categories.get(category, 0) + 1
        return {"documents": len(self.documents), "vault": str(self.vault_path), "categories": categories}


obsidian_memory = ObsidianMemory()
initialize_memory = obsidian_memory.initialize_memory
search_memory = obsidian_memory.search_memory
