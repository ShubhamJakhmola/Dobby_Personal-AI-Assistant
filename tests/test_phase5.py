import json
import tempfile
import unittest
from pathlib import Path

from memory.commands import handle
from memory.context import ContextManager
from memory.conversation import ConversationManager
from memory.long_term import LongTermMemory
from memory.packet import ContextPacket
from memory.project import ProjectContextStore
from memory.policy import sanitize
from memory.task_state import TaskStateStore


class PhaseFiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_context_create_update_clear(self):
        context = ContextManager(self.root)
        self.assertEqual(context.get_current()["topic"], "")
        context.update(topic="Dobby", active_task="memory")
        self.assertEqual(context.get_current()["active_task"], "memory")
        context.clear()
        self.assertEqual(context.get_current()["topic"], "")

    def test_conversation_persistence_and_retrieval(self):
        conversations = ConversationManager(self.root)
        conversations.append("user", "continue Dobby development", project="Dobby")
        self.assertEqual(conversations.recent(1)[0]["project"], "Dobby")
        self.assertEqual(len(conversations.search("Dobby")), 1)

    def test_long_term_create_update_retrieve(self):
        memory = LongTermMemory(self.root)
        record = memory.remember("project", "architecture", "Dobby uses Gemini as its reasoning brain", project="Dobby")
        self.assertEqual(memory.get(record["id"])["value"], record["value"])
        updated = memory.update(record["id"], value="Dobby keeps local execution authority")
        self.assertIn("local", updated["value"])
        self.assertEqual(len(memory.search("local authority", project="Dobby")), 1)

    def test_relevance_and_project_isolation(self):
        memory = LongTermMemory(self.root)
        memory.remember("topic", "garden", "tomatoes and soil", project="Garden")
        memory.remember("project", "runtime", "Dobby action registry and Gemini", project="Dobby")
        context = ContextManager(self.root)
        context.update(topic="software", project="Dobby")
        packet = ContextPacket(self.root, max_memories=5).build("continue Dobby development")
        values = " ".join(item["value"] for item in packet["relevant_memory"])
        self.assertIn("Dobby action registry", values)
        self.assertNotIn("tomatoes", values)

    def test_secret_rejection_and_redaction(self):
        memory = LongTermMemory(self.root)
        with self.assertRaises(ValueError):
            memory.remember("notes", "key", "api_key=abc123456789")
        self.assertEqual(sanitize("password=secret"), "[REDACTED]")

    def test_packet_limits_and_project_context(self):
        context = ContextManager(self.root)
        context.update(project="Dobby", topic="development")
        project = ProjectContextStore(self.root)
        project.upsert("Dobby", workspace="/tmp/dobby", technology=["Python"])
        conversations = ConversationManager(self.root)
        for index in range(20): conversations.append("user", "message " + ("x" * 100))
        packet = ContextPacket(self.root, max_history=20, max_chars=600)
        result = packet.build("message")
        self.assertLessEqual(len(str(result)), 1200)
        self.assertEqual(result["project_context"]["name"], "Dobby")

    def test_explicit_commands(self):
        context = ContextManager(self.root)
        context.update(topic="testing")
        self.assertIn("testing", handle("What is my current context?", self.root))
        self.assertEqual(handle("Clear current context", self.root), "Current context cleared.")

    def test_task_state_is_separate_and_persistent(self):
        path = self.root / "tasks.json"
        store = TaskStateStore(path)
        store.manager.create("task-1", "build")
        self.assertEqual(store.get("task-1")["goal"], "build")
        self.assertTrue(TaskStateStore(path).status()["available"])
        self.assertFalse((self.root / "long_term_records.json").exists())

    def test_corrupt_storage_and_empty_memory_are_safe(self):
        (self.root / "long_term_records.json").write_text("{bad", encoding="utf-8")
        self.assertEqual(LongTermMemory(self.root).search("anything"), [])
        self.assertEqual(ContextManager(self.root).get_current()["topic"], "")


if __name__ == "__main__":
    unittest.main()