"""Herramientas externas con APIs públicas y degradación elegante."""
from __future__ import annotations

import ast
import asyncio
import operator
import os
import re
from urllib.parse import quote
from typing import Any, Dict, List

try:
    import httpx
except ImportError:  # pragma: no cover
    httpx = None


def _extract_city(query: str) -> str:
    """Saca la ciudad de una consulta tipo 'clima en Curitiba' o 'qué tiempo
    hace en Buenos Aires'. Si no puede aislar nada razonable, devuelve ''."""
    q = re.sub(r"(?i).*?\b(clima|tiempo|temperatura|weather)\b\s*(hace\s+)?(de|en|para)?\s*", "", query.strip()).strip()
    q = re.sub(r"[?¿!¡.]+$", "", q).strip()
    return q


def _extract_news_topic(query: str) -> str:
    """Saca el tema de una consulta tipo 'noticias sobre IA' o 'últimas
    noticias de Argentina'. Si no puede aislar nada, devuelve ''."""
    q = re.sub(
        r"(?i)^(dame|dime|decime|busca|buscame|quiero|necesito|mostrame)?\s*(las\s+)?(últimas?\s+)?(noticias|news)\s*(sobre|de|acerca\s+de)?\s*",
        "",
        query.strip(),
    ).strip()
    q = re.sub(r"[?¿!¡.]+$", "", q).strip()
    return q


class ExternalAPIManager:
    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}
        self.timeout = float(self.config.get("api_timeout_sec", 10))

    def get_available_tools(self) -> List[Dict[str, Any]]:
        tavily_available = bool(os.getenv("TAVILY_API_KEY"))
        weather_available = bool(os.getenv("OPENWEATHER_KEY"))
        news_available = bool(os.getenv("NEWSAPI_KEY"))
        return [
            {
                "name": "tavily",
                "description": "Búsqueda web orientada a IA (respuesta sintetizada + fuentes limpias)",
                "available": tavily_available,
            },
            {
                "name": "duckduckgo",
                "description": "Búsqueda web sin clave (respaldo automático si Tavily no está configurada)",
                "available": True,
            },
            {"name": "wikipedia", "description": "Consulta Wikipedia", "available": True},
            {"name": "calculator", "description": "Cálculo aritmético local", "available": True},
            {
                "name": "weather",
                "description": "Clima real vía OpenWeatherMap" if weather_available else "Clima (sin configurar: falta OPENWEATHER_KEY)",
                "available": weather_available,
            },
            {
                "name": "news",
                "description": "Noticias reales vía NewsAPI" if news_available else "Noticias (sin configurar: cae a búsqueda web)",
                "available": news_available,
            },
        ]

    async def search_wikipedia(self, query: str) -> str:
        term = re.sub(r"(?i).*?(wikipedia|qué es|que es)\s*", "", query).strip() or query
        try:
            if httpx is None:
                return "Wikipedia no está disponible sin el paquete httpx."
            url = "https://es.wikipedia.org/api/rest_v1/page/summary/" + quote(term.replace(" ", "_"), safe="")
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                if response.status_code == 404:
                    return "No se encontró información."
                response.raise_for_status()
                data = response.json()
            return str(data.get("extract", "No se encontró información."))
        except (httpx.HTTPError, ValueError):
            return "Wikipedia no está disponible sin conexión."

    async def search_duckduckgo(self, query: str) -> str:
        """Búsqueda web. Usa Tavily si hay TAVILY_API_KEY configurada (incluye
        una respuesta directa sintetizada más las fuentes); si no, cae sola
        a DuckDuckGo. El nombre del método se mantiene por compatibilidad
        con quien ya lo llama (comando /buscar)."""
        from .web_learner import search_internet, get_instant_answer

        answer, rows = await asyncio.gather(
            asyncio.to_thread(get_instant_answer, query),
            asyncio.to_thread(search_internet, query, 5),
        )

        parts: List[str] = []
        if answer:
            parts.append(f"**Respuesta directa:** {answer}")
        sources = "\n".join(f"- {r['title']}: {r['url']}\n  {r['content']}" for r in rows)
        parts.append(sources or "No se encontraron resultados.")
        return "\n\n".join(parts)

    async def get_weather(self, query: str) -> str:
        """Clima real vía OpenWeatherMap. Si no hay OPENWEATHER_KEY en el
        entorno, avisa en vez de fallar en silencio."""
        api_key = os.getenv("OPENWEATHER_KEY", "")
        if not api_key or httpx is None:
            return "Servicio meteorológico no configurado; agregá OPENWEATHER_KEY a tu .env para activarlo."

        city = _extract_city(query)
        if not city:
            return 'Decime de qué ciudad querés el clima (ej: "clima en Curitiba").'

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={"q": city, "appid": api_key, "units": "metric", "lang": "es"},
                )
                if response.status_code == 404:
                    return f'No encontré la ciudad "{city}". Probá agregando el país (ej: "Curitiba,BR").'
                response.raise_for_status()
                data = response.json()

            weather_list = data.get("weather") or [{}]
            desc = str(weather_list[0].get("description", "")).capitalize()
            main = data.get("main", {})
            wind = data.get("wind", {})
            name = data.get("name", city)
            return (
                f"🌤️ **Clima en {name}:** {desc}\n"
                f"- Temperatura: {main.get('temp', '?')}°C (sensación térmica {main.get('feels_like', '?')}°C)\n"
                f"- Humedad: {main.get('humidity', '?')}%\n"
                f"- Viento: {wind.get('speed', '?')} m/s"
            )
        except (httpx.HTTPError, ValueError, KeyError, IndexError):
            return f'No pude consultar el clima de "{city}" en este momento.'

    async def get_news(self, query: str) -> str:
        """Noticias reales vía NewsAPI. Si no hay NEWSAPI_KEY, o la consulta
        falla, cae a búsqueda web normal (Tavily/DuckDuckGo) en vez de dejar
        la respuesta vacía."""
        api_key = os.getenv("NEWSAPI_KEY", "")
        if not api_key or httpx is None:
            return await self.search_duckduckgo(query)

        topic = _extract_news_topic(query)
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    "https://newsapi.org/v2/everything",
                    params={
                        "q": topic or "Argentina",
                        "language": "es",
                        "sortBy": "publishedAt",
                        "pageSize": 5,
                        "apiKey": api_key,
                    },
                )
                response.raise_for_status()
                data = response.json()

            articles = data.get("articles") or []
            if not articles:
                return f'No encontré noticias recientes sobre "{topic or "ese tema"}".'

            label = topic or "la actualidad"
            lines = [f"📰 **Últimas noticias sobre {label}:**"]
            for a in articles[:5]:
                source = (a.get("source") or {}).get("name", "")
                title = a.get("title", "")
                url = a.get("url", "")
                lines.append(f"- {title} ({source}) — {url}")
            return "\n".join(lines)
        except (httpx.HTTPError, ValueError, KeyError):
            return await self.search_duckduckgo(query)

    async def calculate(self, query: str) -> str:
        expr = re.sub(r"(?i).*(?:calcula|calcular|cuánto es|cuanto es)\s*", "", query).strip()
        try:
            allowed = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow: operator.pow}
            def ev(node):
                if isinstance(node, ast.Expression): return ev(node.body)
                if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)): return node.value
                if isinstance(node, ast.BinOp) and type(node.op) in allowed: return allowed[type(node.op)](ev(node.left), ev(node.right))
                raise ValueError("expresión no permitida")
            return str(ev(ast.parse(expr, mode="eval")))
        except Exception:
            return "No pude interpretar el cálculo."

