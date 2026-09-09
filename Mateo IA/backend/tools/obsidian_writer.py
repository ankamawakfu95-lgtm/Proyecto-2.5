"""Persistencia curada de conocimiento en una bóveda Obsidian local."""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


_CATEGORIES = {"knowledge", "projects", "decisions", "procedures", "sources", "daily"}


def _vault(config=None, vault_path=None) -> Path:
    config = config or {}
    selected = (
        vault_path
        or config.get("obsidian_vault")
        or config.get("obsidian_vault_path")
        or __import__("os").environ.get("MATEO_OBSIDIAN_VAULT")
        or __import__("os").environ.get("OBSIDIAN_VAULT_PATH")
        or Path(__file__).resolve().parents[1] / "obsidian"
    )
    return Path(selected).expanduser().resolve()


def _slug(value: str) -> str:
    return re.sub(r"[^\w-]+", "-", value, flags=re.UNICODE).strip("-").lower()[:100] or "nota"


def save_knowledge_to_obsidian(
    topic: str,
    synthesized_content: str,
    sources: Iterable[str] | None = None,
    **kwargs,
) -> str:
    """Guarda una nota útil, trazable y actualizable; rechaza contenido vacío."""
    title = str(topic).strip()
    content = str(synthesized_content).strip()
    if len(title) < 3 or len(content) < 80:
        raise ValueError("La nota no cumple el mínimo de calidad (título o contenido insuficiente).")

    category = str(kwargs.get("category", "knowledge")).lower()
    if category not in _CATEGORIES:
        raise ValueError(f"Categoría no permitida: {category}")

    clean_sources = sorted({str(source).strip() for source in (sources or []) if str(source).strip()})
    if not clean_sources and kwargs.get("require_sources", False):
        raise ValueError("La nota requiere al menos una fuente verificable.")

    vault = _vault(kwargs.get("config"), kwargs.get("vault_path") or kwargs.get("obsidian_vault"))
    target_dir = vault / category
    target_dir.mkdir(parents=True, exist_ok=True)
    path = target_dir / f"{_slug(title)}.md"
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
    tags = kwargs.get("tags", [category])
    tags_text = ", ".join(_slug(str(tag)) for tag in tags if str(tag).strip())
    source_lines = "\n".join(f"- {source}" for source in clean_sources)
    sources_section = f"\n## Fuentes\n{source_lines}\n" if source_lines else ""
    frontmatter = (
        "---\n"
        f"title: {title}\n"
        f"category: {category}\n"
        f"updated: {now}\n"
        f"content_hash: {digest}\n"
        f"tags: [{tags_text}]\n"
        "---\n\n"
    )
    rendered = f"{frontmatter}# {title}\n\n{content}\n{sources_section}"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(rendered, encoding="utf-8")
    temporary.replace(path)
    return str(path)
