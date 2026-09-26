from __future__ import annotations

from development.adapters.aider import AiderAdapter
from development.adapters.claude_code import ClaudeCodeAdapter
from development.adapters.codex import CodexAdapter
from development.adapters.copilot import CopilotAdapter
from development.adapters.gemini_cli import GeminiCliAdapter
from development.adapters.generic_cli import GenericCliAdapter

DEFAULT_ADAPTERS = [AiderAdapter, CodexAdapter, CopilotAdapter, ClaudeCodeAdapter, GeminiCliAdapter]

__all__ = ["GenericCliAdapter", "AiderAdapter", "CodexAdapter", "CopilotAdapter", "ClaudeCodeAdapter", "GeminiCliAdapter", "DEFAULT_ADAPTERS"]
