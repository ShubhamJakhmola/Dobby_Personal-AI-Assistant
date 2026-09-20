from __future__ import annotations

from memory.context import ContextManager
from memory.conversation import ConversationManager
from memory.project import ProjectContextStore
from memory.retrieval import MemoryRetriever
from memory.task_state import TaskStateStore
from pathlib import Path


class ContextPacket:
    def __init__(self, root=None, max_history=6, max_memories=5, max_chars=6000):
        self.context = ContextManager(root)
        self.conversations = ConversationManager(root)
        self.retriever = MemoryRetriever(root)
        self.projects = ProjectContextStore(root)
        self.tasks = TaskStateStore(Path(root) / "tasks.json" if root else None)
        self.max_history, self.max_memories, self.max_chars = max_history, max_memories, max_chars

    def build(self, query: str = "", *, task_id: str = "") -> dict:
        current = self.context.get_current()
        project = self.projects.get(current.get("project", "")) if current.get("project") else None
        packet = {"current_context": current,
                  "task": self.tasks.get(task_id) if task_id else None,
                  "recent_history": self.conversations.recent(self.max_history),
                  "relevant_memory": self.retriever.retrieve_relevant(query, limit=self.max_memories),
                  "project_context": project}
        while len(str(packet)) > self.max_chars and packet["recent_history"]:
            packet["recent_history"].pop(0)
        while len(str(packet)) > self.max_chars and packet["relevant_memory"]:
            packet["relevant_memory"].pop()
        return packet