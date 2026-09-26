from __future__ import annotations

from development.adapters.base import BaseCliAdapter


class ClaudeCodeAdapter(BaseCliAdapter):
    id = "claude_code"
    name = "Claude Code"
    provider = "anthropic"
    executable_names = ("claude", "claude.cmd")
    version_args = ("--version",)
    supports_workspace = True
    supports_headless = True
    supports_noninteractive = False
    known_invocation_styles = ["workspace agent"]
    auth_hint = "not_checked"
