#!/usr/bin/env python3
import sys
import os
import asyncio
from pathlib import Path

# ==========================================
# CONFIGURACION BLINDADA DE RUTAS Y UTF-8
# ==========================================
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

CURRENT_DIR = Path(__file__).parent.resolve()
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))


try:
    from dotenv import load_dotenv
    env_path = CURRENT_DIR / ".env"
    if not env_path.exists():
        env_path = CURRENT_DIR.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    pass

# ==========================================
# IMPORTACIONES DE MATEO
# ==========================================
from core.mateo_ultra_core import MateoUltraCore

# Importaciones para el motor de investigacion
from core.auto_research_engine import AutoResearchEngine

# Importar herramientas reales de Mateo
try:
    from tools import web_learner
except Exception:
    web_learner = None

try:
    from tools.obsidian_memory import obsidian_memory
except Exception:
    obsidian_memory = None

try:
    from tools import obsidian_writer
except Exception:
    obsidian_writer = None


# ==========================================
# PROGRAMADOR DE INVESTIGACION AUTOMATICA
# ==========================================
async def research_scheduler(research_engine):
    """
    Ciclo exacto:
    - FASE ACTIVA: 30 minutos (investiga cada 5 min = 6 veces)
    - FASE DESCANSO: 30 minutos
    - Repetir infinitamente
    """
    while True:
        try:
            print("\n" + "=" * 55)
            print("  FASE ACTIVA: Investigacion automatica (30 min)")
            print("  Investigara 1 tema cada 5 minutos (6 rondas)")
            print("=" * 55)

            for ronda in range(1, 7):
                print(f"\n  [Ronda {ronda}/6] Iniciando investigacion...")
                try:
                    resultado = await research_engine.run_autonomous_research_cycle(max_topics=1)
                    if resultado["success"]:
                        detalles = resultado.get("details", [])
                        for d in detalles:
                            print(f"  -> Tema: {d.get('topic', '?')} | Estado: {d.get('status', '?')}")
                    else:
                        print(f"  -> {resultado.get('message', 'Sin resultados')}")
                except Exception as e:
                    print(f"  -> Error en ronda {ronda}: {e}")

                # Esperar 5 minutos entre rondas (excepto despues de la ultima)
                if ronda < 6:
                    print("  Esperando 5 minutos para la siguiente ronda...")
                    await asyncio.sleep(5 * 60)

            print("\n" + "=" * 55)
            print("  FASE DESCANSO: 30 minutos sin investigar")
            print("=" * 55 + "\n")

            # Descansar 30 minutos
            await asyncio.sleep(30 * 60)

        except asyncio.CancelledError:
            print("\n  Programador de investigacion detenido.")
            break
        except Exception as e:
            print(f"\n  Error grave en el programador: {e}")
            print("  Reintentando en 1 minuto...")
            await asyncio.sleep(60)


# ==========================================
# CONFIGURACION Y CLASE UNIFICADA MATEO ULTRA
# ==========================================
def get_default_config():
    return {
        "max_history": 10,
        "response_default_tokens": 1200,
        "rag_top_k": 4,
        "rag_min_score": 0.25,
        "use_ollama": os.getenv("MATEO_USE_OLLAMA", "true").lower() == "true",
        "ollama_host": os.getenv("MATEO_OLLAMA_HOST", "http://127.0.0.1:11434"),
        "ollama_model": os.getenv("MATEO_OLLAMA_MODEL", "qwen2.5:1.5b"),
        "ollama_timeout_sec": int(os.getenv("MATEO_OLLAMA_TIMEOUT_SEC", 45)),
        "ollama_num_ctx": int(os.getenv("MATEO_OLLAMA_NUM_CTX", 16384)),
        # 🗣️ Muestreo: pensado para que las respuestas suenen naturales y no
        # repetitivas, en vez de deterministas/robóticas (bajar temperature
        # hacia 0.3-0.4 si se prefieren respuestas más literales y estables).
        "ollama_temperature": float(os.getenv("MATEO_OLLAMA_TEMPERATURE", 0.75)),
        "ollama_top_p": float(os.getenv("MATEO_OLLAMA_TOP_P", 0.9)),
        "ollama_top_k": int(os.getenv("MATEO_OLLAMA_TOP_K", 40)),
        "ollama_repeat_penalty": float(os.getenv("MATEO_OLLAMA_REPEAT_PENALTY", 1.15)),
        # 🎭 Temperatura separada por tipo de charla: charla normal más
        # creativa/ingeniosa (amigo), programador/médico más precisos.
        "chat_temperature": float(os.getenv("MATEO_CHAT_TEMPERATURE", 0.95)),
        "precise_temperature": float(os.getenv("MATEO_PRECISE_TEMPERATURE", 0.3)),
        # 🧵 Cuántos turnos recientes (pares user/assistant) se mandan con
        # rol propio al modelo, y a partir de cuántos mensajes acumulados se
        # dispara un resumen de lo más viejo para no perder el hilo en
        # charlas largas.
        "history_turns_in_prompt": int(os.getenv("MATEO_HISTORY_TURNS", 6)),
        "summarize_after_messages": int(os.getenv("MATEO_SUMMARIZE_AFTER", 24)),
        # 🔎 Segunda pasada de auto-revisión sobre la respuesta de charla
        # antes de mostrarla. Mejora coherencia/naturalidad; cuesta una
        # llamada extra al modelo. Poner en "false" para priorizar latencia.
        "enable_reflection": os.getenv("MATEO_ENABLE_REFLECTION", "true").lower() == "true",
        # 🔎 Búsqueda web para /buscar, el ciclo de aprendizaje y la
        # auto-investigación. La clave TAVILY_API_KEY se lee directo del
        # entorno en tools/web_learner.py (no se duplica acá); esto solo
        # controla la profundidad de la búsqueda cuando Tavily está activa.
        "tavily_search_depth": os.getenv("MATEO_TAVILY_SEARCH_DEPTH", "basic"),
        # 🌐 Respaldo en la nube si Ollama no responde. La clave
        # GEMINI_API_KEY se lee directo del entorno en neural/language_model.py
        # (no se duplica acá); esto solo fija qué modelo de Gemini usar.
        # "gemini-flash-latest" sigue siempre al modelo flash recomendado
        # vigente, para no quedar apuntando a una versión que Google
        # discontinúe (como pasó antes con un "gemini-1.5-flash" fijo).
        "gemini_model": os.getenv("MATEO_GEMINI_MODEL", "gemini-flash-latest"),
        "obsidian_vault": os.getenv("MATEO_OBSIDIAN_VAULT", os.getenv("OBSIDIAN_VAULT_PATH", "")),
        "conversation_memory_path": os.getenv("MATEO_CONVERSATION_MEMORY_PATH", ""),
        "conversation_memory_max_turns": int(os.getenv("MATEO_CONVERSATION_MEMORY_MAX_TURNS", 200)),
    }


class MateoUltra:
    """Wrapper integral de Mateo AI Ultra para modo CLI y FastAPI."""

    def __init__(self, config=None):
        self.config = config or get_default_config()
        self.core = MateoUltraCore(self.config)
        self.running = True
        self.research_engine = None
        self.research_task = None

        if AutoResearchEngine and self.core.language_model:
            try:
                self.research_engine = AutoResearchEngine(
                    language_model=self.core.language_model,
                    obsidian_memory_module=obsidian_memory,
                    web_learner_module=web_learner,
                    obsidian_writer_module=obsidian_writer
                )
            except Exception as e:
                print(f"⚠️ Aviso: Motor de investigación automática no inicializado: {e}")

    async def start_background_research(self):
        """Inicia el scheduler de investigación autónoma en segundo plano."""
        if self.research_engine and (not self.research_task or self.research_task.done()):
            self.research_task = asyncio.create_task(research_scheduler(self.research_engine))

    async def shutdown(self):
        """Cierra Mateo y cancela tareas en segundo plano de forma limpia."""
        self.running = False
        if self.research_task and not self.research_task.done():
            self.research_task.cancel()
            try:
                await self.research_task
            except asyncio.CancelledError:
                pass

    def get_stats(self):
        """Obtiene estadísticas de rendimiento del núcleo."""
        return self.core.get_stats()

    async def learn(self, text: str, source: str = "user"):
        """Enseña a Mateo nuevo contenido e indexa en Obsidian."""
        if obsidian_writer and hasattr(obsidian_writer, 'save_knowledge_to_obsidian'):
            from datetime import datetime
            topic = f"Aprendizaje_{source}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            try:
                obsidian_writer.save_knowledge_to_obsidian(
                    topic=topic,
                    synthesized_content=text,
                    sources=[f"Fuente: {source}"],
                    category="knowledge",
                    config=self.config,
                    require_sources=True,
                )
                if obsidian_memory and hasattr(obsidian_memory, 'initialize_memory'):
                    obsidian_memory.initialize_memory()
            except Exception as e:
                print(f"Error guardando aprendizaje: {e}")


# Singleton para uso compartido (API REST y WebSocket)
_mateo_global_instance = None

async def get_mateo() -> MateoUltra:
    """Retorna la instancia global de Mateo AI Ultra."""
    global _mateo_global_instance
    if _mateo_global_instance is None:
        _mateo_global_instance = MateoUltra()
        if os.getenv("MATEO_AUTO_LEARN", "false").lower() == "true":
            await _mateo_global_instance.start_background_research()
    return _mateo_global_instance


# ==========================================
# FUNCION PRINCIPAL (MODO TERMINAL)
# ==========================================
async def main():
    print("Iniciando Mateo AI Ultra...")

    mateo = await get_mateo()
    await mateo.start_background_research()

    print("\n  Mateo está listo para conversar!")
    print("  El motor de investigación automática está corriendo en segundo plano.")
    print("  Escribe 'salir' para terminar\n")

    # ==========================================
    # BUCLE DE CHAT (NO BLOQUEANTE)
    # ==========================================
    while True:
        try:
            user_input = await asyncio.to_thread(input, "Tú: ")
            user_input = user_input.strip()

            if not user_input:
                continue
            if user_input.lower() in ['salir', 'exit', 'quit']:
                print("¡Hasta luego!")
                await mateo.shutdown()
                break

            print("\nMateo está pensando...")
            result = await mateo.core.process_message(user_input)
            print(f"\nMateo: {result['response']}\n")

        except KeyboardInterrupt:
            print("\n¡Hasta luego!")
            await mateo.shutdown()
            break
        except Exception as e:
            print(f"\nError inesperado: {e}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nPrograma interrumpido.")