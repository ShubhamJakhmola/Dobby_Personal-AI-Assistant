from __future__ import annotations

from development.adapters.base import BaseCliAdapter


class CodexAdapter(BaseCliAdapter):
    id = "codex"
    name = "OpenAI Codex"
    provider = "openai"
    executable_names = ("codex", "codex.cmd")
    version_args = ("--version",)
    supports_workspace = True
    supports_headless = True
    supports_noninteractive = False
    known_invocation_styles = ["workspace agent"]
    auth_hint = "not_checked"
