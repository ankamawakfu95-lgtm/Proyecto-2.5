import asyncio
import unittest
from collections import defaultdict
from contextvars import ContextVar

from core.mateo_ultra_core import MateoUltraCore


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


if __name__ == "__main__":
    unittest.main()