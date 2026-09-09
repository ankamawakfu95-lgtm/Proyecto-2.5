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

try:
    import httpx
except ImportError:  # pragma: no cover - depende del entorno
    httpx = None

TAVILY_SEARCH_URL = "https://api.tavily.com/search"


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
            return [
                {"title": str(r.get("title", "")), "url": str(r.get("href", "")), "content": str(r.get("body", ""))}
                for r in rows
            ]
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
        return [
            {"title": str(r.get("title", "")), "url": str(r.get("url", "")), "content": str(r.get("content", ""))}
            for r in data["results"]
        ]

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
