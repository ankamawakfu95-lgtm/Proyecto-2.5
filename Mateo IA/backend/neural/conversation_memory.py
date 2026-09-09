"""Memoria persistente y selectiva de conversaciones por usuario."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


_STOPWORDS = {
    "a", "al", "algo", "como", "con", "de", "del", "el", "en", "es", "esta", "este",
    "hay", "la", "las", "lo", "los", "me", "mi", "mis", "para", "por", "que", "qué",
    "se", "si", "sin", "sobre", "son", "su", "sus", "te", "tu", "tus", "un", "una",
    "uno", "y", "yo", "ya", "the", "is", "to", "of", "and",
}


class ConversationMemory:
    """Persiste conversaciones y recupera solo coincidencias relevantes."""

    def __init__(self, config: Dict[str, Any] | None = None):
        config = config or {}
        configured_path = (
            config.get("conversation_memory_path")
            or os.getenv("MATEO_CONVERSATION_MEMORY_PATH")
        )
        self.path = Path(configured_path or Path(__file__).resolve().parents[1] / "data" / "conversations" / "memory.json").expanduser()
        self.max_turns_per_user = max(10, int(config.get("conversation_memory_max_turns", 200) or 200))
        self.min_score = max(1, int(config.get("conversation_memory_min_score", 2) or 2))
        self._records: Dict[str, List[Dict[str, str]]] = {}
        self._load()

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {
            token for token in re.findall(r"[\wáéíóúüñ]+", str(text).lower(), flags=re.UNICODE)
            if len(token) > 2 and token not in _STOPWORDS
        }

    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(data, dict):
            return
        for user_id, records in data.items():
            if not isinstance(user_id, str) or not isinstance(records, list):
                continue
            clean_records = []
            for record in records[-self.max_turns_per_user:]:
                if not isinstance(record, dict):
                    continue
                user_message = record.get("user")
                assistant_message = record.get("assistant")
                if isinstance(user_message, str) and isinstance(assistant_message, str):
                    clean_records.append({
                        "timestamp": str(record.get("timestamp", "")),
                        "user": user_message[:12000],
                        "assistant": assistant_message[:12000],
                    })
            if clean_records:
                self._records[user_id] = clean_records

    def _persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps(self._records, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def add_turn(self, user_id: str, user_message: str, assistant_message: str) -> None:
        user_id = str(user_id).strip() or "default"
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "user": str(user_message).strip()[:12000],
            "assistant": str(assistant_message).strip()[:12000],
        }
        self._records.setdefault(user_id, []).append(record)
        self._records[user_id] = self._records[user_id][-self.max_turns_per_user:]
        self._persist()

    def search(self, user_id: str, query: str, limit: int = 3) -> List[str]:
        query_tokens = self._tokens(query)
        if not query_tokens:
            return []

        scored = []
        for index, record in enumerate(self._records.get(str(user_id).strip() or "default", [])):
            user_tokens = self._tokens(record["user"])
            assistant_tokens = self._tokens(record["assistant"])
            score = len(query_tokens & user_tokens) * 3 + len(query_tokens & assistant_tokens)
            if score >= self.min_score:
                scored.append((score, index, record))

        scored.sort(key=lambda item: (-item[0], -item[1]))
        return [
            f"Usuario: {record['user']}\nMateo: {record['assistant']}"
            for _, _, record in scored[:max(0, limit)]
        ]

    def clear_user(self, user_id: str) -> None:
        self._records.pop(str(user_id).strip() or "default", None)
        self._persist()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "users": len(self._records),
            "turns": sum(len(records) for records in self._records.values()),
            "path": str(self.path),
        }
