from __future__ import annotations

from development.adapters.base import BaseCliAdapter


class GeminiCliAdapter(BaseCliAdapter):
    id = "gemini_cli"
    name = "Gemini CLI"
    provider = "google"
    executable_names = ("gemini", "gemini.cmd")
    version_args = ("--version",)
    supports_workspace = True
    supports_headless = True
    supports_noninteractive = False
    known_invocation_styles = ["workspace agent"]
    auth_hint = "not_checked"
