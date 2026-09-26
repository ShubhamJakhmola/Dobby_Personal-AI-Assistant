from __future__ import annotations


def normalize_capability(name: str) -> str:
    return str(name or "").strip().lower().replace("_", ".")


def available_capabilities(action_registry) -> set[str]:
    capabilities = set()
    for name in action_registry.names():
        normalized = normalize_capability(name)
        capabilities.add(normalized)
        capabilities.add(normalized.replace(".", "."))
    try:
        from development.agent_registry import CodingAgentRegistry
        for item in CodingAgentRegistry().available():
            capabilities.add(f"coding.agent.{item['id']}")
            capabilities.add(f"coding_agent.{item['id']}")
    except Exception:
        pass
    return capabilities


def missing_capabilities(requested: list[str], action_registry) -> list[str]:
    available = available_capabilities(action_registry)
    return [item for item in requested if normalize_capability(item) not in available]
