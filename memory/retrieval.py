from __future__ import annotations

from memory.context import ContextManager
from memory.conversation import ConversationManager
from memory.long_term import LongTermMemory


class MemoryRetriever:
    def __init__(self, root=None):
        self.context = ContextManager(root)
        self.long_term = LongTermMemory(root)
        self.conversations = ConversationManager(root)

    def retrieve_relevant(self, query: str, *, topic: str | None = None, project: str | None = None,
                          task: str | None = None, limit: int = 5) -> list[dict]:
        state = self.context.get_current()
        topic = topic if topic is not None else state.get("topic", "")
        project = project if project is not None else state.get("project", "")
        task = task if task is not None else state.get("active_task", "")
        results = self.long_term.search(query, topic=topic, project=project, task=task, limit=limit)
        for item in results:
            reasons = []
            if topic and topic.lower() in str(item).lower(): reasons.append(f"matched topic: {topic}")
            if project and project.lower() in str(item).lower(): reasons.append(f"matched project: {project}")
            if set(query.lower().split()) & set(str(item).lower().split()): reasons.append("matched query keywords")
            item["retrieval_reason"] = reasons
        return results