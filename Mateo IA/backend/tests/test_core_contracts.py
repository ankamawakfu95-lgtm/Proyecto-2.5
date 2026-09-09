import asyncio
import unittest
from collections import defaultdict
from contextvars import ContextVar

from core.mateo_ultra_core import MateoUltraCore
from neural.conversation_memory import ConversationMemory
from tools import voice
from tools.web_learner import source_quality
from core.self_improvement_engine import SelfImprovementEngine
from core.learning_cycle import _append_source_catalog, _has_topic_terminology_drift, _has_valid_source_citations, _remove_model_references


class CoreConversationIsolationTests(unittest.TestCase):
    def make_core(self):
        core = object.__new__(MateoUltraCore)
        core._active_user_id = ContextVar("test_active_user_id", default="default")
        core._pending_self_feature = ContextVar("test_pending_self_feature", default=None)
        core._conversation_states = {"default": {"history": [], "summary": ""}}
        core.user_id = "default"
        core.max_history = 10
        core.history_turns_in_prompt = 2
        core.summarize_after_messages = 100
        core.conversation_summary = ""
        core.stats = defaultdict(int)
        core.conversation_memory = None
        return core

    def test_users_have_separate_histories(self):
        core = self.make_core()

        async def exercise():
            await core.process_message("mensaje de Alice", user_id="alice", use_tools=False)
            await core.process_message("mensaje de Bob", user_id="bob", use_tools=False)

        core._retrieve_obsidian_context = lambda message: asyncio.sleep(0, result="")
        core._generate_response = lambda message, context, tool: asyncio.sleep(0, result=f"respuesta a {message}")
        asyncio.run(exercise())

        self.assertEqual([item["content"] for item in core._conversation_states["alice"]["history"]], [
            "mensaje de Alice", "respuesta a mensaje de Alice"
        ])
        self.assertEqual([item["content"] for item in core._conversation_states["bob"]["history"]], [
            "mensaje de Bob", "respuesta a mensaje de Bob"
        ])

    def test_clear_history_only_clears_requested_user(self):
        core = self.make_core()
        core._conversation_states = {
            "alice": {"history": [{"role": "user", "content": "A"}], "summary": "resumen A"},
            "bob": {"history": [{"role": "user", "content": "B"}], "summary": "resumen B"},
        }

        core.clear_history("alice")

        self.assertEqual(core._conversation_states["alice"], {"history": [], "summary": ""})
        self.assertEqual(core._conversation_states["bob"]["history"], [{"role": "user", "content": "B"}])


class QueryClassificationTests(unittest.TestCase):
    def test_explicit_agent_command_is_classified(self):
        core = object.__new__(MateoUltraCore)
        self.assertEqual(core._classify_query("/agente compara Python y Rust"), "agent_task")

    def test_self_referential_question_is_not_wikipedia(self):
        core = object.__new__(MateoUltraCore)
        self.assertNotEqual(core._classify_query("¿Qué es lo que más te gusta?"), "wikipedia")

    def test_self_improvement_confirmations_are_explicit_commands(self):
        core = object.__new__(MateoUltraCore)
        core._pending_self_feature = ContextVar("test_pending_self_feature_commands", default=None)

        self.assertEqual(core._classify_query("/automejora"), "self_improve")
        self.assertEqual(core._classify_query("confirmar `si_4_150359`"), "self_improve")
        self.assertEqual(core._classify_query("aplica las automejoras"), "self_improve")


class ConversationMemoryTests(unittest.TestCase):
    def test_retrieves_only_relevant_user_memory(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            memory = ConversationMemory({"conversation_memory_path": str(Path(directory) / "memory.json")})
            memory.add_turn("leonardo", "Estoy aprendiendo Python", "Qué bueno, puedo ayudarte con Python.")

            self.assertEqual(len(memory.search("leonardo", "¿Qué estoy aprendiendo?")), 1)
            self.assertEqual(memory.search("leonardo", "Hola, ¿cómo estás?"), [])
            self.assertEqual(memory.search("otra-persona", "¿Qué estoy aprendiendo?"), [])

    def test_clear_removes_persistent_user_memory(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            memory = ConversationMemory({"conversation_memory_path": str(Path(directory) / "memory.json")})
            memory.add_turn("leonardo", "Mi editor es VS Code", "Lo tendré en cuenta.")
            memory.clear_user("leonardo")
            self.assertEqual(memory.search("leonardo", "¿Qué editor uso?"), [])

    def test_memory_file_survives_new_instance(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.json"
            first = ConversationMemory({"conversation_memory_path": str(path)})
            first.add_turn("leonardo", "Estoy estudiando bases de datos", "Puedo ayudarte con SQL.")

            second = ConversationMemory({"conversation_memory_path": str(path)})
            self.assertEqual(len(second.search("leonardo", "¿Qué estoy estudiando?")), 1)


class VoiceConfigurationTests(unittest.TestCase):
    def test_whisper_defaults_to_cpu_without_cuda(self):
        from unittest.mock import patch

        with patch.dict("os.environ", {}, clear=False):
            with patch.dict("os.environ", {"MATEO_WHISPER_DEVICE": "", "MATEO_WHISPER_COMPUTE_TYPE": ""}):
                self.assertEqual(voice._whisper_runtime_options(), {"device": "cpu", "compute_type": "int8"})

    def test_whisper_cuda_can_be_enabled_explicitly(self):
        from unittest.mock import patch

        with patch.dict("os.environ", {"MATEO_WHISPER_DEVICE": "cuda", "MATEO_WHISPER_COMPUTE_TYPE": "float16"}):
            self.assertEqual(voice._whisper_runtime_options(), {"device": "cuda", "compute_type": "float16"})


class SelfImprovementAnalysisTests(unittest.TestCase):
    def test_analysis_reads_code_after_old_truncation_limit(self):
        class RecordingModel:
            def __init__(self):
                self.prompts = []

            async def generate(self, prompt):
                self.prompts.append(prompt)
                return "[]"

        model = RecordingModel()
        engine = SelfImprovementEngine(model)
        code = "inicio\n" + ("x = 1\n" * 500) + "MARCADOR_FINAL\n"

        result = asyncio.run(engine._propose_improvements({"archivo.py": code}, "tools"))

        self.assertEqual(result, [])
        self.assertTrue(model.prompts)
        self.assertTrue(any("MARCADOR_FINAL" in prompt for prompt in model.prompts))

    def test_analysis_preserves_and_scans_large_files_in_chunks(self):
        class RecordingModel:
            def __init__(self):
                self.prompts = []

            async def generate(self, prompt):
                self.prompts.append(prompt)
                return "[]"

        model = RecordingModel()
        engine = SelfImprovementEngine(model)
        code = "A" * (engine.ANALYSIS_CHUNK_CHARS + 100) + "MARCADOR_FINAL"

        asyncio.run(engine._propose_improvements({"archivo.py": code}, "all"))

        self.assertEqual(len(model.prompts), 2)
        self.assertTrue(any("MARCADOR_FINAL" in prompt for prompt in model.prompts))


class LearningQualityTests(unittest.TestCase):
    def test_model_references_are_replaced_by_real_source_catalog(self):
        draft = "## Desarrollo\nDato [Fuente 1].\n\n## Referencias\nFuente inventada"
        clean = _remove_model_references(draft)
        catalog = _append_source_catalog(clean, [{"title": "Fuente oficial", "url": "https://example.org/oficial"}])

        self.assertNotIn("Fuente inventada", catalog)
        self.assertIn("https://example.org/oficial", catalog)

    def test_learning_rejects_known_terminology_drift(self):
        self.assertTrue(_has_topic_terminology_drift(
            "inteligencia artificial explicable",
            "La inteligencia artificial explotable es...",
        ))
        self.assertFalse(_has_topic_terminology_drift(
            "inteligencia artificial explicable",
            "La inteligencia artificial explicable es...",
        ))

    def test_source_quality_prioritizes_institutional_domains(self):
        self.assertGreater(source_quality("https://www.who.int/health"), source_quality("https://example.com/article"))
        self.assertEqual(source_quality("https://docs.python.org/3/"), 1.0)

    def test_citations_must_reference_existing_sources(self):
        self.assertTrue(_has_valid_source_citations("Hecho [Fuente 1].", 2))
        self.assertFalse(_has_valid_source_citations("Hecho [Fuente 3].", 2))
        self.assertFalse(_has_valid_source_citations("Hecho sin referencia.", 2))

    def test_learning_cycle_sends_full_source_content_and_urls(self):
        from unittest.mock import patch
        import core.learning_cycle as learning_cycle

        marker = "MARCADOR_DE_EVIDENCIA_" + ("x" * 1200)
        saved = {}

        class Memory:
            def search_memory(self, topic, k=2):
                return ["Conocimiento previo suficiente sobre el tema."]

        class Model:
            async def generate(self, prompt, **kwargs):
                self.prompt = prompt
                return "## Resumen\n" + ("Contenido respaldado. " * 15) + "[Fuente 1]"

        model = Model()
        results = [{
            "title": "Fuente institucional",
            "url": "https://docs.python.org/3/",
            "content": marker,
            "source_quality": 1.0,
        }]

        def fake_save(topic, content, sources, **kwargs):
            saved["sources"] = sources
            saved["content"] = content
            return "nota.md"

        with patch.object(learning_cycle, "obsidian_memory", Memory()), \
                patch.object(learning_cycle, "search_internet", return_value=results), \
                patch.object(learning_cycle, "save_knowledge_to_obsidian", side_effect=fake_save):
            response = asyncio.run(learning_cycle.execute_learning_cycle("Python", model))

        self.assertIn("He aprendido", response)
        self.assertIn(marker, model.prompt)
        self.assertIn("https://docs.python.org/3/", saved["sources"][0])

    def test_learning_cycle_rejects_uncited_synthesis(self):
        from unittest.mock import patch
        import core.learning_cycle as learning_cycle

        class Model:
            async def generate(self, prompt, **kwargs):
                return "## Resumen\n" + ("Texto sin respaldo. " * 20)

        results = [{"title": "Fuente", "url": "https://example.org", "content": "Evidencia real."}]
        with patch.object(learning_cycle, "obsidian_memory", None), \
                patch.object(learning_cycle, "search_internet", return_value=results):
            response = asyncio.run(learning_cycle.execute_learning_cycle("Tema", Model()))

        self.assertIn("no fue fiable", response)

if __name__ == "__main__":
    unittest.main()