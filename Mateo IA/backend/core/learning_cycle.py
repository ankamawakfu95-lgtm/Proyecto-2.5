import logging
from tools.web_learner import search_internet
from tools.obsidian_writer import save_knowledge_to_obsidian
from tools.obsidian_memory import obsidian_memory

logger = logging.getLogger(__name__)

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
    web_results = search_internet(f"{topic} explicación detallada artículo", num_results=3)
    
    if not web_results:
        return f"No pude encontrar información relevante en internet sobre '{topic}'."
    
    # 3. Extraer URLs y el contenido limpio que ya nos da la búsqueda web
    urls = [r["url"] for r in web_results]
    
    # Unimos el contenido limpio (limitamos a 3 para no saturar el contexto de Ollama)
    raw_content = "\n\n---\n\n".join([
        f"FUENTE: {r['url']}\nCONTENIDO:\n{r['content']}" 
        for r in web_results[:3]
    ])
    
    # 4. Sintetizar con tu LLM
    prompt = f"""Eres Mateo, una IA en constante evolución.
Conocimiento previo en tu bóveda: {context_prev}

Nueva información de internet (ya limpia y extraída): 
{raw_content}

TAREA: Sintetiza un resumen estructurado, profundo y claro sobre "{topic}". 
Integra lo que ya sabías con la nueva información. Usa markdown, viñetas y negritas.
No menciones que eres una IA ni que estás resumiendo, solo entrega el conocimiento final."""
    
    synthesized_text = ""
    try:
        if language_model and hasattr(language_model, 'generate'):
            synthesized_text = await language_model.generate(prompt)
        elif language_model and hasattr(language_model, 'invoke'):
            synthesized_text = await language_model.invoke(prompt)
        else:
            synthesized_text = "El modelo de lenguaje no está disponible."
            
        # Limpieza robusta de la respuesta
        if isinstance(synthesized_text, dict):
            synthesized_text = synthesized_text.get('text', str(synthesized_text))
        elif hasattr(synthesized_text, 'content'):
            synthesized_text = synthesized_text.content
            
        if not synthesized_text or len(str(synthesized_text).strip()) < 10:
            raise ValueError("Respuesta del LLM vacía o demasiado corta.")
            
    except Exception as e:
        logger.error(f"❌ FALLA EN EL MODELO DE LENGUAJE: {e}")
        return f"No guardé la investigación porque la síntesis no fue fiable. Fuentes encontradas: {', '.join(urls)}"

    # 5. Guardar en Obsidian
    save_result = save_knowledge_to_obsidian(
        topic,
        str(synthesized_text).strip(),
        urls,
        category="knowledge",
        require_sources=True,
    )
    
    # 6. Recargar memoria para que el nuevo archivo esté disponible
    try:
        obsidian_memory.initialize_memory()
    except Exception:
        pass
    
    return f"✅ He aprendido sobre '{topic}'.\n\n{synthesized_text}\n\n📂 {save_result}"