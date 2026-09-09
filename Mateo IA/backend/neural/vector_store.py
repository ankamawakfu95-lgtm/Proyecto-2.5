"""Almacén vectorial local ligero; Chroma se usa sólo si está instalado."""
from __future__ import annotations

import math
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List


class VectorStore:
    def __init__(self, config: Dict[str, Any] | None = None):
        config = config or {}
        root = Path(config.get("data_dir", Path(__file__).resolve().parents[1] / "data"))
        self.persist_directory = Path(config.get("vector_store_path", root / "vectors" / "local")).expanduser()
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self._storage_path = self.persist_directory / "documents.json"
        self._documents: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        """Carga la memoria creada en ejecuciones anteriores."""
        try:
            data = json.loads(self._storage_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self._documents = [
                    {
                        "id": str(item.get("id", index)),
                        "text": item["text"],
                        "metadata": item.get("metadata", {}),
                    }
                    for index, item in enumerate(data)
                    if isinstance(item, dict) and isinstance(item.get("text"), str)
                ]
        except (OSError, json.JSONDecodeError):
            self._documents = []

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"\w+", text.lower(), flags=re.UNICODE))

    def add_documents(self, documents: Iterable[Any], metadatas: Iterable[Dict[str, Any]] | None = None, **_: Any) -> List[str]:
        metadata = list(metadatas or [])
        ids = []
        for index, document in enumerate(documents):
            text = getattr(document, "page_content", document)
            text = str(text)
            item_metadata = metadata[index] if index < len(metadata) and isinstance(metadata[index], dict) else {}
            item_id = str(item_metadata.get("id", len(self._documents)))
            if any(item["id"] == item_id for item in self._documents):
                item_id = f"{item_id}-{len(self._documents)}"
            self._documents.append({"id": item_id, "text": text, "metadata": item_metadata})
            ids.append(item_id)
        self.persist()
        return ids

    def add_texts(self, texts: Iterable[str], metadatas: Iterable[Dict[str, Any]] | None = None, **kwargs: Any) -> List[str]:
        return self.add_documents(texts, metadatas, **kwargs)

    def similarity_search(self, query: str, k: int = 4, **_: Any) -> List[str]:
        q = self._tokens(query)
        scored = []
        for item in self._documents:
            tokens = self._tokens(item["text"])
            score = len(q & tokens) / math.sqrt(max(1, len(q) * len(tokens)))
            scored.append((score, item["id"], item["text"]))
        return [text for score, _, text in sorted(scored, key=lambda item: (-item[0], item[1]))[:max(0, k)] if score > 0]

    def search(self, query: str, k: int = 4, **kwargs: Any) -> List[str]:
        return self.similarity_search(query, k, **kwargs)

    def persist(self) -> None:
        temporary = self._storage_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self._documents, ensure_ascii=False, indent=2), encoding="utf-8")
        temporary.replace(self._storage_path)

    def get_stats(self) -> Dict[str, Any]:
        return {"documents": len(self._documents), "path": str(self.persist_directory)}
