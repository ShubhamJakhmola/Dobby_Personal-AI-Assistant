from __future__ import annotations

from memory.packet import ContextPacket


class BrainContextBroker:
    def __init__(self, root=None):
        self.root = root

    def build(self, request) -> dict:
        requirements = request.context_requirements or {}
        packet = ContextPacket(self.root,
                               max_history=requirements.get("recent_history", 6),
                               max_memories=requirements.get("relevant_memory", 5),
                               max_chars=min(request.max_context, requirements.get("max_characters", request.max_context)))
        return packet.build(request.task, task_id=request.metadata.get("task_id", ""))