from __future__ import annotations

from development.adapters.base import BaseCliAdapter


class CopilotAdapter(BaseCliAdapter):
    id = "copilot"
    name = "GitHub Copilot"
    provider = "github"
    executable_names = ("gh", "gh.exe")
    version_args = ("--version",)
    supports_workspace = True
    supports_headless = False
    supports_noninteractive = False
    known_invocation_styles = ["gh extension or IDE integration"]
    auth_hint = "not_checked"
