"""
Motor de Agente Autónomo de Mateo ("Modo Agente")
==================================================
Inspirado en la arquitectura de AgentGPT (planificar -> ejecutar -> generar
nuevas tareas -> resumir), pero reimplementado desde cero para funcionar
100% local con el mismo Ollama que ya usa Mateo:

- Sin OpenAI, sin LangChain, sin Pinecone/AWS ni claves nuevas.
- Reutiliza las herramientas que Mateo ya tiene: búsqueda web (Tavily/
  DuckDuckGo), Wikipedia, calculadora y la propia bóveda de Obsidian.
- Pensado para objetivos concretos y acotados ("investigá X y armame un
  resumen", "compará A y B y decime cuál conviene"), no para tareas
  abiertas de días de duración: hay topes duros de tareas e iteraciones
  para que nunca quede corriendo indefinidamente ni se pase de contexto.

Flujo (una llamada a run(objetivo) hace todo esto):
  1. _create_initial_tasks   -> hasta 5 subtareas concretas (JSON)
  2. por cada tarea pendiente (tope duro de pasos):
       _analyze_task         -> elige UNA herramienta para esa tarea
       _execute_task          -> la ejecuta de verdad
       _create_followup_task -> el modelo decide si hace falta 1 tarea más
  3. _summarize               -> informe final en markdown
  4. (opcional) guarda el informe final como nota en la bóveda de Obsidian

No reemplaza al motor de auto-mejora (que modifica código) ni al ciclo de
aprendizaje (pensado para una sola búsqueda + nota). Este módulo es para
objetivos de varios pasos que combinan herramientas distintas.
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any, Awaitable, Callable, Dict, List, Optional

try:
    from utils.logger import setup_logger
    logger = setup_logger("MateoAgentEngine")
except Exception:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


# Herramientas que el agente puede elegir para cada subtarea.
TOOLS = ["buscar_web", "wikipedia", "calculadora", "memoria_obsidian", "razonar"]

# Topes duros de seguridad: un objetivo mal planteado nunca debe dejar al
# agente corriendo indefinidamente ni golpeando la web sin límite.
MAX_INITIAL_TASKS = 5
MAX_TOTAL_STEPS = 8
MAX_RESULT_CHARS = 1400  # lo que se reinyecta al modelo por cada resultado

OnStepCallback = Optional[Callable[[Dict[str, Any]], Awaitable[None]]]


def _truncate(text: str, limit: int = MAX_RESULT_CHARS) -> str:
    text = str(text or "").strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "…"


def _extract_json_array(text: str) -> Optional[List[str]]:
    """Busca el primer array JSON de strings dentro de una respuesta del
    modelo (que a veces agrega texto alrededor pese a que se le pidió JSON
    puro). Devuelve None si no encuentra nada usable."""
    match = re.search(r"\[.*\]", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except (ValueError, TypeError):
        return None
    if not isinstance(data, list):
        return None
    cleaned = [str(item).strip() for item in data if str(item).strip()]
    return cleaned or None


class AgentEngine:
    """Bucle de agente autónomo acotado, construido sobre los componentes
    que MateoUltraCore ya inicializó (modelo de lenguaje, APIs externas,
    memoria de Obsidian)."""

    def __init__(self, core: Any):
        # Referencia al MateoUltraCore ya inicializado: reutilizamos su
        # modelo de lenguaje y sus herramientas en vez de crear los propios.
        self.core = core

    # ==========================================
    # PASO 1: PLANIFICACIÓN INICIAL
    # ==========================================
    async def _create_initial_tasks(self, goal: str) -> List[str]:
        prompt = (
            "Sos un planificador de tareas. Te doy un objetivo y devolvés una lista de "
            "hasta 5 subtareas concretas y breves, en español, necesarias para lograrlo. "
            "Cada subtarea debe poder resolverse con UNA de estas acciones: buscar en la "
            "web, consultar Wikipedia, hacer un cálculo, revisar la memoria propia de "
            "Mateo, o razonar directamente sobre la información disponible.\n\n"
            "Respondé ÚNICAMENTE con un array JSON de strings, sin texto antes ni "
            "después, sin explicaciones. Ejemplos de formato:\n"
            '["Buscar las últimas noticias sobre el tema", "Calcular el total de X"]\n\n'
            f'OBJETIVO: "{goal}"'
        )
        try:
            raw = await self.core.language_model.generate(prompt, max_tokens=400, temperature=0.3)
        except Exception as e:
            logger.warning(f"⚠️ No se pudo planificar tareas iniciales: {e}")
            raw = ""

        tasks = _extract_json_array(raw or "")
        if not tasks:
            # Si el modelo no devolvió JSON usable, tratamos el objetivo
            # completo como una única tarea en vez de fallar.
            return [goal]
        return tasks[:MAX_INITIAL_TASKS]

    # ==========================================
    # PASO 2a: ELEGIR HERRAMIENTA PARA UNA TAREA
    # ==========================================
    async def _analyze_task(self, goal: str, task: str) -> str:
        prompt = (
            f"Objetivo general: \"{goal}\"\n"
            f"Tarea actual: \"{task}\"\n\n"
            f"Elegí UNA sola herramienta de esta lista para resolver la tarea actual: "
            f"{', '.join(TOOLS)}.\n"
            "- buscar_web: para información actual, noticias, hechos externos.\n"
            "- wikipedia: para definiciones o datos enciclopédicos estables.\n"
            "- calculadora: solo si la tarea es una cuenta matemática explícita.\n"
            "- memoria_obsidian: para revisar qué sabe Mateo ya guardado en su propia bóveda.\n"
            "- razonar: si la tarea se resuelve pensando con la información ya reunida, sin buscar nada nuevo.\n\n"
            "Respondé ÚNICAMENTE con el nombre exacto de la herramienta elegida, nada más."
        )
        try:
            raw = await self.core.language_model.generate(prompt, max_tokens=20, temperature=0.0)
        except Exception as e:
            logger.warning(f"⚠️ No se pudo analizar la tarea '{task}': {e}")
            return "razonar"

        raw_lower = (raw or "").lower()
        for tool in TOOLS:
            if tool in raw_lower:
                return tool
        return "razonar"

    # ==========================================
    # PASO 2b: EJECUTAR LA TAREA CON LA HERRAMIENTA ELEGIDA
    # ==========================================
    async def _execute_task(self, goal: str, task: str, tool: str) -> str:
        try:
            if tool == "buscar_web" and self.core.api_manager:
                return await self.core.api_manager.search_duckduckgo(task)

            if tool == "wikipedia" and self.core.api_manager:
                return await self.core.api_manager.search_wikipedia(task)

            if tool == "calculadora" and self.core.api_manager:
                return await self.core.api_manager.calculate(task)

            if tool == "memoria_obsidian":
                context = await self.core._retrieve_obsidian_context(task)
                return context or "No encontré nada relevante en la bóveda de Obsidian para esto."

            # "razonar" o cualquier herramienta no disponible: el propio
            # modelo resuelve la subtarea con lo que ya sabe.
            reasoning_prompt = (
                f"Objetivo general: \"{goal}\"\n"
                f"Subtarea a resolver: \"{task}\"\n\n"
                "Resolvé esta subtarea de forma directa y concreta, en español. "
                "Si necesitás tomar una decisión, tomala vos mismo con tu propio criterio "
                "y explicá brevemente por qué."
            )
            return await self.core.language_model.generate(reasoning_prompt, max_tokens=500, temperature=0.5)
        except Exception as e:
            logger.warning(f"⚠️ Error ejecutando la tarea '{task}' con '{tool}': {e}")
            return f"No pude completar esta subtarea ({e})."

    # ==========================================
    # PASO 2c: PROPONER UNA TAREA DE SEGUIMIENTO (0 o 1)
    # ==========================================
    async def _create_followup_task(
        self, goal: str, pending_tasks: List[str], last_task: str, last_result: str
    ) -> Optional[str]:
        prompt = (
            f"Objetivo general: \"{goal}\"\n"
            f"Tareas pendientes: {pending_tasks or 'ninguna'}\n"
            f"Tarea recién completada: \"{last_task}\"\n"
            f"Resultado obtenido: \"{_truncate(last_result, 600)}\"\n\n"
            "Si hace falta UNA tarea más (y solo una) para acercarse al objetivo, "
            "respondé con una sola frase describiéndola, sin comillas ni numeración. "
            "Si ya hay tareas pendientes suficientes o no hace falta ninguna tarea "
            "nueva, respondé exactamente: NINGUNA"
        )
        try:
            raw = await self.core.language_model.generate(prompt, max_tokens=80, temperature=0.3)
        except Exception as e:
            logger.warning(f"⚠️ No se pudo proponer tarea de seguimiento: {e}")
            return None

        candidate = (raw or "").strip().strip('"')
        if not candidate or candidate.upper().startswith("NINGUNA"):
            return None
        return candidate

    # ==========================================
    # PASO 3: INFORME FINAL
    # ==========================================
    async def _summarize(self, goal: str, steps: List[Dict[str, Any]]) -> str:
        transcript = "\n\n".join(
            f"### Tarea: {s['tarea']}\n(herramienta: {s['herramienta']})\n{_truncate(s['resultado'], 700)}"
            for s in steps
        )
        prompt = (
            f"Objetivo original: \"{goal}\"\n\n"
            f"Se completaron estas tareas para lograrlo:\n\n{transcript}\n\n"
            "Redactá un informe final en markdown, en español, que responda al objetivo "
            "original usando SOLO la información reunida arriba. Usá encabezados y listas "
            "donde ayude a la claridad. No inventes datos que no estén en la información "
            "reunida. Si la información reunida no alcanza para cubrir algo del objetivo, "
            "decilo explícitamente en vez de completarlo de memoria."
        )
        try:
            return await self.core.language_model.generate(prompt, max_tokens=900, temperature=0.4)
        except Exception as e:
            logger.warning(f"⚠️ No se pudo generar el informe final: {e}")
            return transcript

    # ==========================================
    # BUCLE PRINCIPAL
    # ==========================================
    async def run(
        self,
        goal: str,
        max_steps: int = MAX_TOTAL_STEPS,
        on_step: OnStepCallback = None,
        save_to_obsidian: bool = False,
    ) -> Dict[str, Any]:
        """Ejecuta el objetivo de punta a punta y devuelve un dict con el
        desglose de pasos y el informe final. `on_step`, si se pasa, se
        llama (con await) después de cada tarea completada — pensado para
        que quien invoque el motor pueda ir mostrando progreso en vivo
        (por ejemplo por WebSocket) sin tener que esperar al resultado
        completo."""
        goal = str(goal).strip()
        if not goal:
            return {"objetivo": goal, "pasos": [], "informe_final": "No se recibió un objetivo válido."}

        max_steps = max(1, min(int(max_steps), MAX_TOTAL_STEPS))
        pending_tasks = await self._create_initial_tasks(goal)
        steps: List[Dict[str, Any]] = []
        done_tasks_lower: List[str] = []

        while pending_tasks and len(steps) < max_steps:
            task = pending_tasks.pop(0)

            # Evita reprocesar una tarea casi idéntica a una ya hecha
            # (protección simple contra loops del propio modelo).
            if any(task.lower() in seen or seen in task.lower() for seen in done_tasks_lower):
                continue

            tool = await self._analyze_task(goal, task)
            result = await self._execute_task(goal, task, tool)
            step = {"tarea": task, "herramienta": tool, "resultado": result}
            steps.append(step)
            done_tasks_lower.append(task.lower())

            if on_step:
                try:
                    await on_step(step)
                except Exception as e:
                    logger.warning(f"⚠️ on_step falló (se ignora, no interrumpe el agente): {e}")

            if len(steps) < max_steps and not pending_tasks:
                followup = await self._create_followup_task(goal, pending_tasks, task, result)
                if followup:
                    pending_tasks.append(followup)

        final_report = await self._summarize(goal, steps) if steps else "No se pudo completar ninguna tarea para este objetivo."

        saved_path: Optional[str] = None
        if save_to_obsidian and final_report and len(final_report.strip()) >= 80:
            try:
                from tools.obsidian_writer import save_knowledge_to_obsidian
                sources = [s["tarea"] for s in steps if s["herramienta"] == "buscar_web"]
                saved_path = save_knowledge_to_obsidian(
                    topic=f"Agente - {goal}"[:100],
                    synthesized_content=final_report,
                    sources=sources,
                    category="projects",
                    tags=["agente_autonomo"],
                    config=self.core.config,
                )
            except Exception as e:
                logger.warning(f"⚠️ No se pudo guardar el informe del agente en Obsidian: {e}")

        return {
            "objetivo": goal,
            "pasos": steps,
            "informe_final": (final_report or "").strip(),
            "guardado_en_obsidian": saved_path,
        }

    def format_chat_response(self, result: Dict[str, Any]) -> str:
        """Arma el texto que se muestra en el chat normal (comando /agente),
        con el desglose de pasos y el informe final en un solo mensaje."""
        lines = [f"🤖 **Modo Agente** — objetivo: {result['objetivo']}\n"]
        for i, step in enumerate(result["pasos"], 1):
            lines.append(f"**Paso {i}** ({step['herramienta']}): {step['tarea']}")
        lines.append("\n---\n")
        lines.append(result["informe_final"] or "No se generó un informe final.")
        if result.get("guardado_en_obsidian"):
            lines.append(f"\n📥 Guardado en la bóveda: `{result['guardado_en_obsidian']}`")
        return "\n".join(lines)
