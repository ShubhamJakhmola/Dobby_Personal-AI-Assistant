"""Risk classification for actions before they reach the operating system."""
from __future__ import annotations

from dataclasses import dataclass
import re

L0 = 0
L1 = 1
L2 = 2
L3 = 3


@dataclass(frozen=True)
class PolicyDecision:
    level: int
    allowed: bool
    requires_confirmation: bool
    reason: str = ""

    @property
    def risk_level(self) -> str:
        return f"L{self.level}"


_PRIVILEGED = re.compile(r"(^|\s)(sudo|su|doas|pkexec)(\s|$)")
_DESTRUCTIVE = re.compile(
    r"(?:\brm\s+-[a-z]*r[a-z]*f|\bmkfs(?:\.|\s)|\bdd\s+if=|\b(shutdown|reboot|poweroff)\b|"
    r"\b(delete|destroy|drop\s+database|truncate\s+table)\b|/dev/(?:sd|nvme|vd)[a-z])",
    re.IGNORECASE,
)
_SECRET_OR_EXTERNAL = re.compile(
    r"(?:password|passphrase|api[_ -]?key|secret|private key|credential|token|upload|send[_ -]?(?:email|message)|publish|purchase|payment)",
    re.IGNORECASE,
)


def classify(action: str, parameters: dict | None = None) -> PolicyDecision:
    name = str(action or "").strip().lower()
    params = parameters or {}
    if name == "media_control":
        return PolicyDecision(L1, True, False)
    if name == "system_intelligence":
        operation = str(params.get("operation", "")).lower()
        if operation in {"cleanup", "kill", "terminate", "stop", "safe_stop"}:
            return PolicyDecision(L2, True, False)
        return PolicyDecision(L0, True, False)
    if name == "troubleshoot":
        return PolicyDecision(L0, True, False)
    if name in {"terminal_execute", "process_manager", "application_manager"}:
        operation = str(params.get("operation", "")).lower()
        if name == "terminal_execute":
            command = params.get("command", [])
            text = " ".join(command) if isinstance(command, list) else str(command)
            if _PRIVILEGED.search(text) or _DESTRUCTIVE.search(text):
                return PolicyDecision(L3, False, True, "privileged or destructive command")
            if _SECRET_OR_EXTERNAL.search(text):
                return PolicyDecision(L3, False, True, "secret or external-impact command")
            return PolicyDecision(L1, True, False)
        if operation in {"stop", "restart", "delete", "disable"}:
            return PolicyDecision(L2, True, False)
        return PolicyDecision(L1, True, False)
    if name in {"computer_input", "computer_clipboard", "computer_window", "computer_application"}:
        text = jsonish(params)
        if _SECRET_OR_EXTERNAL.search(text):
            return PolicyDecision(L3, False, True, "sensitive keyboard or clipboard content")
        return PolicyDecision(L1, True, False)
    if name == "computer_screen":
        return PolicyDecision(L0, True, False)
    if name in {"filesystem_create_file", "filesystem_edit_file", "task_scheduler"}:
        operation = str(params.get("operation", "create")).lower()
        if operation in {"delete", "destroy", "remove", "wipe"}:
            return PolicyDecision(L3, False, True, "destructive file or scheduled-task operation")
        return PolicyDecision(L2, True, False)
    if _SECRET_OR_EXTERNAL.search(name) or _SECRET_OR_EXTERNAL.search(jsonish(params)):
        return PolicyDecision(L3, False, True, "secret, external, or financial consequence")
    return PolicyDecision(L0, True, False)


def jsonish(value: object) -> str:
    """Flatten untrusted action arguments for classification without executing them."""
    if isinstance(value, dict):
        return " ".join(f"{key} {jsonish(item)}" for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return " ".join(jsonish(item) for item in value)
    return str(value or "")