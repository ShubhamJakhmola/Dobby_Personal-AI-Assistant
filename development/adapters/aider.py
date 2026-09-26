from __future__ import annotations

from development.adapters.base import BaseCliAdapter


class AiderAdapter(BaseCliAdapter):
    id = "aider"
    name = "Aider"
    provider = "aider"
    executable_names = ("aider", "aider.cmd")
    version_args = ("--version",)
    supports_workspace = True
    supports_headless = True
    supports_noninteractive = False
    known_invocation_styles = ["repository workspace"]
    auth_hint = "not_checked"
