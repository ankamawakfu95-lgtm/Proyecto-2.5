"""Adaptador de LLM con Ollama local como motor principal y Gemini como
respaldo en la nube.

- generate(prompt): completions de texto libre (investigación, auto-mejora,
  generación de documentos). Usa /api/generate de Ollama.
- chat(messages): conversación estructurada por turnos (charla, programador,
  modo médico). Usa /api/chat de Ollama, que respeta el chat-template real
  del modelo (system/user/assistant) en vez de aplastar todo en un único
  string de texto plano.

En ambos casos, el modelo principal SIEMPRE es el que corre en Ollama local
(por defecto qwen2.5:1.5b). Gemini solo entra como respaldo automático si
Ollama no responde (proceso caído, modelo no descargado, sin red hacia
127.0.0.1, etc.) y hay GEMINI_API_KEY configurada — así Mateo no se queda
sin poder responder por un problema puntual del servidor local.
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

try:  # httpx es opcional: el modo fallback sigue funcionando sin él.
    import httpx
except ImportError:  # pragma: no cover - depende del entorno
    httpx = None


class NeuralLanguageProcessor:
    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}
        self.use_ollama = bool(self.config.get("use_ollama", True))
        self.ollama_host = str(self.config.get("ollama_host", "http://127.0.0.1:11434")).rstrip("/")
        self.ollama_model = str(self.config.get("ollama_model", "qwen2.5:1.5b"))
        self.timeout = float(self.config.get("ollama_timeout_sec", 45))
        self.model_name = str(self.config.get("model_name", "local"))

        # Parámetros de muestreo por defecto, pensados para conversación
        # fluida y natural (no para respuestas deterministas de una sola
        # palabra). Todos son configurables desde get_default_config() sin
        # tocar este archivo.
        self.num_ctx = int(self.config.get("ollama_num_ctx", 8192))
        self.temperature = float(self.config.get("ollama_temperature", 0.75))
        self.top_p = float(self.config.get("ollama_top_p", 0.9))
        self.top_k = int(self.config.get("ollama_top_k", 40))
        self.repeat_penalty = float(self.config.get("ollama_repeat_penalty", 1.15))
        self.repeat_last_n = int(self.config.get("ollama_repeat_last_n", 256))

        # 🌐 Respaldo en la nube (Gemini). La clave se lee directo del
        # entorno (GEMINI_API_KEY en tu .env); config puede pisarla si hace
        # falta, pero no se duplica el valor en get_default_config().
        self.gemini_api_key = str(self.config.get("gemini_api_key") or os.getenv("GEMINI_API_KEY", "")).strip()
        self.gemini_model = str(self.config.get("gemini_model") or os.getenv("MATEO_GEMINI_MODEL", "gemini-flash-latest"))
        self.gemini_timeout = float(self.config.get("gemini_timeout_sec", 30))
        # Se actualiza en cada llamada: "ollama" o "gemini", útil para logs/stats.
        self.last_provider: str = "ollama"

    def _base_options(self, **overrides: Any) -> Dict[str, Any]:
        options = {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "repeat_penalty": self.repeat_penalty,
            "repeat_last_n": self.repeat_last_n,
            "num_ctx": self.num_ctx,
        }
        for key in ("temperature", "top_p", "top_k", "repeat_penalty", "num_ctx"):
            if key in overrides and overrides[key] is not None:
                options[key] = overrides[key]
        if "max_tokens" in overrides and overrides["max_tokens"] is not None:
            options["num_predict"] = overrides["max_tokens"]
        if "num_predict" in overrides and overrides["num_predict"] is not None:
            options["num_predict"] = overrides["num_predict"]
        return options

    # ==========================================
    # 🌐 RESPALDO EN LA NUBE (GEMINI)
    # ==========================================
    async def _gemini_generate_contents(
        self,
        contents: List[Dict[str, Any]],
        system_text: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """Llama a la API de Gemini (generateContent). Devuelve "" ante
        cualquier falla (sin clave, sin red, error HTTP, respuesta rara),
        para que quien la llama pueda seguir con el mensaje final de
        fallback en vez de romperse."""
        if httpx is None or not self.gemini_api_key or not contents:
            return ""
        body: Dict[str, Any] = {"contents": contents}
        if system_text:
            body["systemInstruction"] = {"parts": [{"text": system_text}]}
        gen_config: Dict[str, Any] = {}
        if kwargs.get("temperature") is not None:
            gen_config["temperature"] = kwargs["temperature"]
        max_tokens = kwargs.get("max_tokens") or kwargs.get("num_predict")
        if max_tokens:
            gen_config["maxOutputTokens"] = int(max_tokens)
        if gen_config:
            body["generationConfig"] = gen_config

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent"
        try:
            async with httpx.AsyncClient(timeout=self.gemini_timeout) as client:
                response = await client.post(
                    url,
                    headers={"x-goog-api-key": self.gemini_api_key, "Content-Type": "application/json"},
                    json=body,
                )
                response.raise_for_status()
                data = response.json()
                candidates = data.get("candidates") or []
                if not candidates:
                    return ""
                parts = (candidates[0].get("content") or {}).get("parts") or []
                text = "".join(str(p.get("text", "")) for p in parts).strip()
                return text
        except (httpx.HTTPError, ValueError, OSError, KeyError, IndexError, TypeError):
            return ""

    async def generate(self, prompt: str, **kwargs: Any) -> str:
        """Genera mediante Ollama local a partir de un único bloque de texto;
        si Ollama no responde, cae a Gemini (si hay clave configurada).

        Pensado para completions de texto libre (redacción de documentos,
        síntesis de investigación, propuestas de auto-mejora), no para
        turnos de charla. Para conversación usar chat().
        """
        if not isinstance(prompt, str) or not prompt.strip():
            return ""
        if self.use_ollama and httpx is not None:
            payload = {
                "model": self.ollama_model,
                "prompt": prompt,
                "stream": False,
                "options": self._base_options(**kwargs),
            }
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(f"{self.ollama_host}/api/generate", json=payload)
                    response.raise_for_status()
                    data = response.json()
                    self.last_provider = "ollama"
                    return str(data.get("response", "")).strip()
            except (httpx.HTTPError, ValueError, OSError):
                pass

        if self.gemini_api_key:
            fallback_text = await self._gemini_generate_contents(
                [{"role": "user", "parts": [{"text": prompt}]}], **kwargs
            )
            if fallback_text:
                self.last_provider = "gemini"
                return fallback_text

        return "[Modo local] No hay un modelo de lenguaje disponible para responder (Ollama y Gemini fallaron o no están configurados)."

    async def chat(self, messages: List[Dict[str, str]], **kwargs: Any) -> str:
        """Genera una respuesta a partir de una lista de turnos con roles.

        `messages` debe ser una lista de dicts {"role": "system"|"user"|"assistant",
        "content": str}, en orden cronológico. Usar esto para cualquier
        interacción conversacional: respeta el chat-template del modelo, lo
        que produce respuestas más coherentes y con mejor seguimiento del
        hilo que concatenar todo en un solo prompt de texto. Si Ollama no
        responde, cae a Gemini (si hay clave) antes de aplanar a generate().
        """
        if not messages:
            return ""
        clean_messages = [
            {"role": m.get("role", "user"), "content": str(m.get("content", ""))}
            for m in messages
            if str(m.get("content", "")).strip()
        ]
        if not clean_messages:
            return ""

        if self.use_ollama and httpx is not None:
            payload = {
                "model": self.ollama_model,
                "messages": clean_messages,
                "stream": False,
                "options": self._base_options(**kwargs),
            }
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(f"{self.ollama_host}/api/chat", json=payload)
                    response.raise_for_status()
                    data = response.json()
                    message = data.get("message") or {}
                    text = message.get("content", "")
                    if not text and data.get("response"):
                        text = data["response"]
                    if text:
                        self.last_provider = "ollama"
                        return str(text).strip()
            except (httpx.HTTPError, ValueError, OSError):
                pass

        if self.gemini_api_key:
            system_text = "\n\n".join(m["content"] for m in clean_messages if m["role"] == "system") or None
            gemini_contents = [
                {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                for m in clean_messages
                if m["role"] != "system"
            ]
            fallback_text = await self._gemini_generate_contents(gemini_contents, system_text=system_text, **kwargs)
            if fallback_text:
                self.last_provider = "gemini"
                return fallback_text

        # Último recurso: si ni /api/chat de Ollama ni Gemini funcionaron,
        # aplanamos los turnos y probamos generate() (que en su propia
        # cadena de fallback también reintenta Gemini una vez más).
        flattened = "\n".join(f"{m['role']}: {m['content']}" for m in clean_messages) + "\nassistant:"
        return await self.generate(flattened, **kwargs)

    async def invoke(self, prompt: str, **kwargs: Any) -> str:
        return await self.generate(prompt, **kwargs)

    def get_available_tools(self) -> List[Dict[str, Any]]:
        return [
            {"name": "ollama", "description": f"Generación mediante Ollama local ({self.ollama_model})", "available": self.use_ollama},
            {
                "name": "gemini",
                "description": f"Respaldo en la nube ({self.gemini_model}) si Ollama no responde",
                "available": bool(self.gemini_api_key),
            },
        ]
