"""
Motor de Investigación y Evolución de Conocimiento Automático (Nivel 3)
Permite a Mateo profundizar en temas que ya conoce, buscar información nueva
y actualizar su memoria de Obsidian de forma autónoma.
"""
import asyncio
import json
import re
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger("AutoResearchEngine")

MAX_RESEARCH_RESULTS = 6
MAX_RESEARCH_CONTENT = 6000

class AutoResearchEngine:
    # CORRECCIÓN 1: Constructor correcto
    def __init__(self, language_model, obsidian_memory_module, web_learner_module, obsidian_writer_module):
        """
        language_model: Instancia de NeuralLanguageProcessor (tiene .generate())
        obsidian_memory_module: Módulo tools.obsidian_memory (tiene .search_memory())
        web_learner_module: Módulo tools.web_learner (tiene función de búsqueda)
        obsidian_writer_module: Módulo tools.obsidian_writer (tiene save_knowledge_to_obsidian)
        """
        self.language_model = language_model
        self.obsidian_memory = obsidian_memory_module
        self.web_learner = web_learner_module
        self.obsidian_writer = obsidian_writer_module
        self.research_history = []
        base_dir = Path(__file__).resolve().parent.parent.parent
        self.researched_topics_file = base_dir / "backend" / "data" / "researched_topics.json"
        self.researched_topics = self._load_researched_topics()



    def _load_researched_topics(self) -> set:
        """Carga temas ya investigados para no repetirlos."""
        try:
            if self.researched_topics_file.exists():
                with open(self.researched_topics_file, "r", encoding="utf-8") as f:
                    return set(json.load(f))
        except Exception:
            pass
        return set()

    def _save_researched_topic(self, topic: str):
        """Guarda tema como ya investigado."""
        self.researched_topics.add(topic)
        try:
            self.researched_topics_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.researched_topics_file, "w", encoding="utf-8") as f:
                json.dump(list(self.researched_topics), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error guardando temas investigados: {e}")

    async def run_autonomous_research_cycle(self, max_topics: int = 1) -> Dict[str, Any]:
        """Ejecuta un ciclo completo: seleccionar tema -> analizar brechas -> investigar -> guardar."""
        logger.info(f"Iniciando ciclo de investigacion automatica. Objetivo: {max_topics} temas.")
        results = []

        # 1. Seleccionar temas conocidos de Obsidian
        known_topics = self._select_known_topics(max_topics)
        if not known_topics:
            logger.info("No se encontraron temas en la memoria para investigar.")
            return {"success": False, "message": "No hay temas conocidos para investigar aun."}

        for topic_info in known_topics:
            topic_name = topic_info["title"]
            topic_content = topic_info["content"]

            # CORRECCIÓN 2: Evitar repetir temas
            if topic_name in self.researched_topics:
                logger.info(f"Tema '{topic_name}' ya investigado. Saltando.")
                continue

            logger.info(f"Investigando tema: {topic_name}")
            try:
                # 2. Identificar brechas de conocimiento
                queries = await self._identify_knowledge_gaps(topic_name, topic_content)
                if not queries:
                    logger.info(f"No se encontraron brechas para '{topic_name}'. Saltando.")
                    continue

                # 3. Investigar en la web
                new_data = await self._gather_new_data(queries)

                # 4. Sintetizar y actualizar memoria
                synthesis_result = await self._synthesize_and_update(
                    topic_name, topic_content, new_data, queries
                )
                results.append(synthesis_result)

                # Marcar como investigado
                self._save_researched_topic(topic_name)

            except Exception as e:
                logger.error(f"Error investigando '{topic_name}': {e}")
                results.append({"topic": topic_name, "status": "error", "error": str(e)})

        return {
            "success": len(results) > 0,
            "topics_researched": len(results),
            "details": results
        }

    def _select_known_topics(self, count: int) -> List[Dict[str, Any]]:
        """Selecciona temas de la memoria de Obsidian."""
        try:
            if not self.obsidian_memory:
                return []

            # CORRECCIÓN 3: Queries más variadas para encontrar diferentes temas
            search_queries = [
                "inteligencia artificial", "programacion", "python",
                "machine learning", "datos", "tecnologia", "ciencia",
                "medicina", "biologia", "fisica", "matematicas",
                "economia", "psicologia", "filosofia", "historia",
                "arte", "musica", "literatura", "deportes"
            ]

            all_docs = []
            for query in search_queries:
                try:
                    docs = self.obsidian_memory.search_memory(query, k=3)
                    if docs:
                        for doc in docs:
                            # Extraer un título del contenido
                            first_line = doc.strip().split("\n")[0] if doc.strip() else "Sin titulo"
                            title = first_line.replace("#", "").strip()[:80]
                            if not title:
                                title = query

                            # CORRECCIÓN 4: Filtrar temas ya investigados
                            if title not in self.researched_topics:
                                all_docs.append({"title": title, "content": doc})
                except Exception:
                    continue

            if not all_docs:
                return []

            # Eliminar duplicados por título
            seen = set()
            unique_docs = []
            for doc in all_docs:
                if doc["title"] not in seen:
                    seen.add(doc["title"])
                    unique_docs.append(doc)

            # Seleccionar aleatoriamente
            selected = random.sample(unique_docs, min(count, len(unique_docs)))
            return selected

        except Exception as e:
            logger.error(f"Error seleccionando temas: {e}")
            return []

    async def _identify_knowledge_gaps(self, topic_name: str, topic_content: str) -> List[str]:
        """Usa el LLM para generar consultas de búsqueda que profundicen el tema."""
        prompt_lines = [
            "Eres Mateo. Tienes esta nota en tu memoria:",
            "",
            f"TEMA: {topic_name}",
            f"CONTENIDO ACTUAL: {topic_content[:1200]}",
            "",
            "TAREA: Genera exactamente 2 consultas de busqueda especificas",
            "para buscar en internet y profundizar en este tema.",
            "Las consultas deben ser cortas y directas (como las que usarias en Google).",
            "",
            "Devuelve SOLO un JSON con este formato exacto:",
            '{"queries": ["consulta 1", "consulta 2"]}',
            "",
            "No escribas nada mas, solo el JSON."
        ]
        prompt = "\n".join(prompt_lines)

        try:
            response = await self.language_model.generate(prompt, max_tokens=200)
            response_text = str(response).strip()
            if hasattr(response, 'content'):
                response_text = response.content.strip()
            elif isinstance(response, dict) and 'text' in response:
                response_text = response['text'].strip()

            json_match = re.search(r'\{.*?\}', response_text, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                queries = data.get("queries", [])
                if isinstance(queries, list) and len(queries) > 0:
                    return queries[:2]  # Máximo 2 queries por tema para ahorrar recursos

            return []
        except Exception as e:
            logger.error(f"Error identificando brechas: {e}")
            return []

    async def _gather_new_data(self, queries: List[str]) -> List[Dict[str, Any]]:
        """Busca información nueva en la web."""
        collected = []
        for query in queries:
            try:
                logger.info(f"Buscando en la web: {query}")
                if self.web_learner and hasattr(self.web_learner, 'search_internet'):
                    # CORRECCIÓN 5: Usar search_internet (la función correcta de tu web_learner)
                    results = await asyncio.to_thread(
                        self.web_learner.search_internet,
                        query,
                        num_results=MAX_RESEARCH_RESULTS,
                    )
                    for result in results[:MAX_RESEARCH_RESULTS]:
                        collected.append({
                            "query": query,
                            "title": result.get("title", "Sin título"),
                            "url": result.get("url", ""),
                            "data": result.get("content", "")[:MAX_RESEARCH_CONTENT],
                            "source_quality": result.get("source_quality", 0),
                        })
                elif self.web_learner and hasattr(self.web_learner, 'search_and_extract'):
                    results = await self.web_learner.search_and_extract(
                        query, num_results=MAX_RESEARCH_RESULTS
                    )
                    for result in results[:MAX_RESEARCH_RESULTS]:
                        collected.append({
                            "query": query,
                            "title": result.get("title", "Sin título"),
                            "url": result.get("url", ""),
                            "data": result.get("content", "")[:MAX_RESEARCH_CONTENT],
                            "source_quality": result.get("source_quality", 0),
                        })
                else:
                    logger.warning("web_learner no tiene metodo de busqueda compatible.")
                    collected.append({"query": query, "data": "No disponible"})
            except Exception as e:
                logger.warning(f"Error buscando '{query}': {e}")
                collected.append({"query": query, "data": f"Error: {e}"})
        return collected

    async def _synthesize_and_update(self, topic_name: str, original_content: str,
                                      new_data: List, queries: List) -> Dict[str, Any]:
        """Fusiona lo viejo con lo nuevo y guarda en Obsidian."""
        new_data_text = "\n\n".join([
            (
                f"[Fuente {index}]\n"
                f"Título: {data.get('title', 'Sin título')}\n"
                f"URL: {data.get('url', '')}\n"
                f"Consulta: {data.get('query', '')}\n"
                f"Contenido:\n{data.get('data', '')[:MAX_RESEARCH_CONTENT]}"
            )
            for index, data in enumerate(new_data, 1)
        ])

        prompt_lines = [
            "Eres Mateo. Estas actualizando tu propia memoria de conocimiento.",
            "",
            f"TEMA: {topic_name}",
            "",
            "CONOCIMIENTO PREVIO:",
            original_content[:4000],
            "",
            "NUEVA INFORMACION INVESTIGADA:",
            new_data_text,
            "",
            "TAREA: Escribe una nota completa, profunda y bien estructurada en Markdown.",
            "Usa únicamente afirmaciones respaldadas por las fuentes recibidas.",
            "Cita cada afirmación importante con [Fuente N].",
            "Separa hechos, interpretaciones y controversias.",
            "Si no hay evidencia suficiente, dilo claramente y no inventes.",
            "Usa los encabezados ## Resumen, ## Desarrollo, ## Evidencia y límites y ## Conclusión.",
            "Elimina redundancias y conserva una redacción seria, clara y original."
        ]
        prompt = "\n".join(prompt_lines)

        try:
            synthesized = await self.language_model.generate(prompt, max_tokens=2500, temperature=0.35)
            synthesized_text = str(synthesized).strip()
            if hasattr(synthesized, 'content'):
                synthesized_text = synthesized.content.strip()
            elif isinstance(synthesized, dict) and 'text' in synthesized:
                synthesized_text = synthesized['text'].strip()

            citation_numbers = {
                int(number) for number in re.findall(r"\[Fuente\s+(\d+)\]", synthesized_text, re.IGNORECASE)
            }
            if len(synthesized_text) < 200 or not citation_numbers or not all(
                1 <= number <= len(new_data) for number in citation_numbers
            ):
                raise ValueError("La síntesis no contiene citas válidas a las fuentes recibidas.")

            # Guardar en Obsidian
            if self.obsidian_writer and hasattr(self.obsidian_writer, 'save_knowledge_to_obsidian'):
                # CORRECCIÓN 6: Nombres de archivos legibles
                topic_id = topic_name
                sources = [
                    f"[Fuente {index}] {data.get('title', 'Sin título')} - {data.get('url', '')}"
                    for index, data in enumerate(new_data, 1)
                    if data.get("url")
                ]

                try:
                    self.obsidian_writer.save_knowledge_to_obsidian(
                        topic=topic_id,
                        synthesized_content=synthesized_text,
                        sources=sources,
                        category="knowledge",
                        require_sources=True,
                    )
                    logger.info(f"Memoria actualizada: {topic_id}")
                except TypeError:
                    # Si la función es async
                    await self.obsidian_writer.save_knowledge_to_obsidian(
                        topic=topic_id,
                        synthesized_content=synthesized_text,
                        sources=sources
                    )
                    logger.info(f"Memoria actualizada (async): {topic_id}")

            self.research_history.append({
                "topic": topic_name,
                "timestamp": datetime.now().isoformat(),
                "queries": queries
            })

            return {
                "topic": topic_name,
                "status": "updated",
                "queries_used": len(queries)
            }

        except Exception as e:
            logger.error(f"Error sintetizando '{topic_name}': {e}")
            return {"topic": topic_name, "status": "failed", "error": str(e)}