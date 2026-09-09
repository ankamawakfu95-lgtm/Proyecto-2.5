"""Búsqueda web para investigación y aprendizaje.

Proveedor principal: Tavily (pensado específicamente para consumo por LLMs:
devuelve contenido ya limpio y relevante, no HTML crudo con ruido, y puede
generar una respuesta sintetizada directa). Si no hay TAVILY_API_KEY
configurada, o la llamada falla por cualquier motivo (sin red, rate limit,
etc.), cae automáticamente a DuckDuckGo (no requiere clave) sin romper nada
en el resto del sistema: /buscar, el ciclo de aprendizaje
(core/learning_cycle.py) y el motor de auto-investigación
(core/auto_research_engine.py) siguen funcionando igual, solo mejora la
calidad de lo que reciben.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

try:
    import httpx
except ImportError:  # pragma: no cover - depende del entorno
    httpx = None

TAVILY_SEARCH_URL = "https://api.tavily.com/search"

_TRUSTED_DOMAIN_SUFFIXES = (
    ".gov", ".gob", ".edu", ".ac.uk", ".who.int", ".int",
)
_TRUSTED_DOMAINS = {
    "wikipedia.org", "nature.com", "science.org", "sciencedirect.com",
    "arxiv.org", "ncbi.nlm.nih.gov", "nih.gov", "cochranelibrary.com",
    "openstax.org", "python.org", "docs.python.org",
}


def source_quality(url: str) -> float:
    """Devuelve una puntuación heurística, no una garantía de veracidad."""
    parsed = urlparse(str(url))
    host = parsed.netloc.lower().split(":", 1)[0]
    host = host.removeprefix("www.")
    if not host or parsed.scheme not in {"http", "https"}:
        return 0.0
    if host in _TRUSTED_DOMAINS or any(host.endswith(suffix.strip()) for suffix in _TRUSTED_DOMAIN_SUFFIXES):
        return 1.0
    if host.endswith(".org"):
        return 0.65
    return 0.45


def _normalize_result(result: Dict[str, Any]) -> Dict[str, Any]:
    url = str(result.get("url") or result.get("href") or "").strip()
    return {
        "title": str(result.get("title", "")).strip(),
        "url": url,
        "content": str(result.get("content") or result.get("body") or "").strip(),
        "score": result.get("score"),
        "source_quality": source_quality(url),
    }


def _tavily_request(
    query: str,
    num_results: int,
    api_key: str,
    search_depth: str = "basic",
    include_answer: bool = False,
    timeout: float = 15.0,
) -> Optional[Dict[str, Any]]:
    """Llama a la API de Tavily. Devuelve None ante cualquier falla (sin
    clave, sin red, error HTTP, respuesta rara) para que quien la llama
    pueda caer a DuckDuckGo sin más."""
    if httpx is None or not api_key:
        return None
    payload = {
        "api_key": api_key,
        "query": str(query),
        "search_depth": search_depth if search_depth in ("basic", "advanced") else "basic",
        "max_results": max(1, min(int(num_results), 10)),
        "include_answer": bool(include_answer),
    }
    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(TAVILY_SEARCH_URL, json=payload)
            response.raise_for_status()
            return response.json()
    except (httpx.HTTPError, ValueError, OSError):
        return None


def _search_duckduckgo(query: str, num_results: int) -> List[Dict[str, str]]:
    """Respaldo sin clave: se usa si Tavily no está configurada o falla.

    El paquete `duckduckgo_search` fue renombrado a `ddgs` (el viejo dejó de
    recibir actualizaciones y ya no trae resultados confiables). Probamos
    primero el paquete nuevo y activo; si no está instalado, caemos al
    nombre viejo por compatibilidad con instalaciones existentes."""
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS  # compatibilidad con instalaciones viejas
        with DDGS() as search:
            rows = search.text(str(query), max_results=max(1, int(num_results)))
            results = [
                _normalize_result(r)
                for r in rows
            ]
            return sorted(results, key=lambda item: item["source_quality"], reverse=True)
    except Exception as e:
        # Antes esto se tragaba el error en silencio y Mateo decía "no
        # encontré nada" incluso cuando el problema era, por ejemplo, un
        # paquete faltante o desactualizado. Ahora queda en el log para
        # poder diagnosticarlo.
        import logging
        logging.getLogger("MateoWebLearner").warning(f"⚠️ Búsqueda web (DDG/ddgs) falló: {e}")
        return []


def search_internet(query: str, num_results: int = 5, **kwargs: Any) -> List[Dict[str, str]]:
    """Busca en la web y devuelve resultados con {title, url, content}.

    Intenta primero Tavily (mejor contenido para RAG/aprendizaje) y si no
    hay clave o falla, usa DuckDuckGo. kwargs opcionales: tavily_api_key,
    tavily_search_depth ("basic" o "advanced"; "advanced" busca más a fondo
    pero consume más créditos de la cuenta de Tavily).
    """
    if not str(query).strip():
        return []

    api_key = kwargs.get("tavily_api_key") or os.getenv("TAVILY_API_KEY", "")
    search_depth = kwargs.get("tavily_search_depth") or os.getenv("MATEO_TAVILY_SEARCH_DEPTH", "basic")

    data = _tavily_request(query, num_results, api_key, search_depth=search_depth)
    if data and data.get("results"):
        results = [_normalize_result(r) for r in data["results"]]
        return sorted(results, key=lambda item: item["source_quality"], reverse=True)

    return _search_duckduckgo(query, num_results)


def search_and_extract(query: str, num_results: int = 5) -> List[Dict[str, str]]:
    return search_internet(query, num_results=num_results)


def get_instant_answer(query: str, num_results: int = 5) -> str:
    """Pide a Tavily una respuesta ya sintetizada (include_answer=True).

    Solo funciona si hay TAVILY_API_KEY configurada; si no, o si Tavily no
    devuelve una respuesta clara, devuelve "" (nunca falla ni bloquea:
    quien la llama simplemente la ignora y sigue con los resultados
    normales de search_internet)."""
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        return ""
    data = _tavily_request(
        query,
        num_results,
        api_key,
        search_depth=os.getenv("MATEO_TAVILY_SEARCH_DEPTH", "basic"),
        include_answer=True,
    )
    if data:
        return str(data.get("answer") or "").strip()
    return ""
