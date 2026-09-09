import logging
import re
from tools.web_learner import search_internet
from tools.obsidian_writer import save_knowledge_to_obsidian
from tools.obsidian_memory import obsidian_memory

logger = logging.getLogger(__name__)

MAX_SEARCH_RESULTS = 6
MAX_SOURCE_CONTENT = 6000


def _model_text(response) -> str:
    if isinstance(response, dict):
        return str(response.get("text") or response.get("content") or "").strip()
    if hasattr(response, "content"):
        return str(response.content).strip()
    return str(response or "").strip()


def _has_valid_source_citations(text: str, source_count: int) -> bool:
    citations = {int(number) for number in re.findall(r"\[Fuente\s+(\d+)\]", text, re.IGNORECASE)}
    return bool(citations) and all(1 <= number <= source_count for number in citations)

async def execute_learning_cycle(topic: str, language_model):
    """Orquesta la búsqueda, comprensión y guardado de nuevo conocimiento
    (Tavily si hay TAVILY_API_KEY configurada, si no DuckDuckGo automáticamente)."""
    logger.info(f"🚀 Iniciando ciclo de aprendizaje autónomo sobre: {topic}")

    # 1. Buscar contexto previo en la memoria de Obsidian
    try:
        prev_knowledge = obsidian_memory.search_memory(topic, k=2)
        context_prev = "\n".join(prev_knowledge) if prev_knowledge else "No hay conocimiento previo en la bóveda."
    except Exception as e:
        logger.warning(f"⚠️ No se pudo buscar en Obsidian: {e}")
        context_prev = "No hay conocimiento previo."

    # 2. Buscar en internet (Tavily o, si no hay clave, DuckDuckGo; ya devuelve contenido limpio)
    web_results = search_internet(
        f"{topic} explicación detallada evidencia fuentes confiables",
        num_results=MAX_SEARCH_RESULTS,
    )

    if not web_results:
        return f"No pude encontrar información relevante en internet sobre '{topic}'."

    # 3. Extraer URLs y el contenido limpio que ya nos da la búsqueda web
    urls = [r["url"] for r in web_results]

    # Conservamos más evidencia, pero con un límite por fuente para controlar el contexto.
    raw_content = "\n\n---\n\n".join([
        (
            f"[Fuente {index}]\n"
            f"Título: {result.get('title', 'Sin título')}\n"
            f"URL: {result.get('url', '')}\n"
            f"Calidad heurística del dominio: {result.get('source_quality', 0):.2f}\n"
            f"Contenido:\n{result.get('content', '')[:MAX_SOURCE_CONTENT]}"
        )
        for index, result in enumerate(web_results[:MAX_SEARCH_RESULTS], 1)
    ])

    # 4. Sintetizar con tu LLM
    prompt = f"""Eres Mateo, una IA en constante evolución.
Conocimiento previo en tu bóveda: {context_prev}

Nueva información de internet (ya limpia y extraída):
{raw_content}

TAREA: Redacta una nota profunda, clara y original sobre "{topic}".
Usa únicamente afirmaciones respaldadas por la evidencia recibida.
Después de cada afirmación importante coloca una cita como [Fuente 1].
Separa explícitamente hechos, interpretaciones y posibles controversias.
Si las fuentes no permiten confirmar algo, dilo claramente y no lo inventes.
Organiza la nota con: ## Resumen, ## Desarrollo, ## Evidencia y límites,
## Conclusión. Usa Markdown, buena redacción y ejemplos solo si están respaldados.
No menciones que eres una IA ni que estás resumiendo."""

    synthesized_text = ""
    try:
        if language_model and hasattr(language_model, 'generate'):
            synthesized_text = await language_model.generate(prompt, max_tokens=2500, temperature=0.35)
        elif language_model and hasattr(language_model, 'invoke'):
            synthesized_text = await language_model.invoke(prompt, max_tokens=2500, temperature=0.35)
        else:
            synthesized_text = "El modelo de lenguaje no está disponible."

        synthesized_text = _model_text(synthesized_text)
        if len(synthesized_text) < 200:
            raise ValueError("Respuesta del LLM vacía o demasiado corta.")
        if not _has_valid_source_citations(synthesized_text, min(len(web_results), MAX_SEARCH_RESULTS)):
            raise ValueError("La síntesis no contiene citas válidas a las fuentes recibidas.")

    except Exception as e:
        logger.error(f"❌ FALLA EN EL MODELO DE LENGUAJE: {e}")
        return f"No guardé la investigación porque la síntesis no fue fiable. Fuentes encontradas: {', '.join(urls)}"

    # 5. Guardar en Obsidian
    source_references = [
        f"[Fuente {index}] {result.get('title', 'Sin título')} - {result.get('url', '')}"
        for index, result in enumerate(web_results[:MAX_SEARCH_RESULTS], 1)
    ]
    save_result = save_knowledge_to_obsidian(
        topic,
        str(synthesized_text).strip(),
        source_references,
        category="knowledge",
        require_sources=True,
    )

    # 6. Recargar memoria para que el nuevo archivo esté disponible
    try:
        obsidian_memory.initialize_memory()
    except Exception:
        pass

    return f"✅ He aprendido sobre '{topic}'.\n\n{synthesized_text}\n\n📂 {save_result}"