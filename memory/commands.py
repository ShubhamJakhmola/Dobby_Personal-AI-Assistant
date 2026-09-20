from __future__ import annotations

import re

from memory.context import ContextManager
from memory.long_term import LongTermMemory
from memory.retrieval import MemoryRetriever
from memory.storage import memory_root


def handle(command: str, root=None) -> str | None:
    text = re.sub(r"[^\w\s]", "", command.strip().lower()).strip()
    context = ContextManager(root)
    memory = LongTermMemory(root)
    if text in {"what do you remember", "show saved memory", "show recent memory", "memory list"}:
        return str(memory.search(limit=20))
    if text == "memory status":
        return str({"path": str(memory_root(root)), "records": len(memory.search(limit=100000)), "context": context.get_current()})
    if text.startswith("memory search "):
        return str(memory.search(text.removeprefix("memory search "), limit=20))
    if text in {"what is my current context", "show current context", "context show"}:
        return str(context.get_current())
    if text in {"clear current context", "clear context"}:
        context.clear()
        return "Current context cleared."
    if text.startswith("forget this") or text.startswith("forget memory"):
        record_id = text.split()[-1] if len(text.split()) > 2 else ""
        return "Memory forgotten." if record_id and memory.delete(record_id) else "Specify the memory id to forget."
    if text.startswith("why did you use that memory"):
        return "Memory retrieval is based on deterministic topic, project, and keyword matches."
    return None