"""Provider-independent intent representation and conservative local parsing."""
from __future__ import annotations

import json
import re
import shlex
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Intent:
    goal: str
    intent: str
    parameters: dict = field(default_factory=dict)
    constraints: dict = field(default_factory=dict)
    expected_outcome: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


class IntentParser:
    def parse(self, request: str) -> Intent:
        text = request.strip()
        lower = text.lower()
        if lower.startswith(("run ", "execute ")):
            command_text = text.split(" ", 1)[1]
            return Intent(text, "terminal.execute", {"command": shlex.split(command_text)},
                          expected_outcome={"exit_code": 0})
        cron = re.search(r"(?:run|execute)\s+(\S+).*every day at\s+(\d{1,2})(?::(\d{2}))?\s*(?:am|pm)?", lower)
        if cron:
            path = str(Path(cron.group(1)).expanduser())
            hour = int(cron.group(2))
            if "pm" in lower and hour < 12:
                hour += 12
            if "am" in lower and hour == 12:
                hour = 0
            return Intent(text, "scheduler.create", {
                "name": f"dobby_{Path(path).stem}", "schedule": f"0 {hour} * * *",
                "command": [sys.executable, path],
            }, expected_outcome={"schedule_exists": True})
        port = re.search(r"(?:using|on)\s+port\s+(\d+)", lower)
        if port and any(word in lower for word in ("check", "what", "process")):
            return Intent(text, "network.port_process", {"port": int(port.group(1))},
                          expected_outcome={"query_completed": True})
        start = re.match(r"(?:please\s+)?start\s+(.+)$", text, re.IGNORECASE)
        if start:
            name = start.group(1).strip()
            return Intent(text, "process.start", {"operation": "start", "command": shlex.split(name)},
                          expected_outcome={"process_running": True})
        create = re.match(r"(?:please\s+)?create\s+(?:a\s+)?(?:file\s+)?([^\s]+)(?:\s+in\s+(.+))?$", text, re.IGNORECASE)
        if create:
            location = (create.group(2) or "").strip().lower()
            base = Path.cwd() if location in {"current directory", "the current directory", "here"} else Path(location).expanduser() if location else Path.cwd()
            path = (base / create.group(1)).expanduser() if location else Path(create.group(1)).expanduser()
            return Intent(text, "filesystem.create_file", {"path": str(path), "content": ""},
                          expected_outcome={"file_exists": True})
        return Intent(text, "unknown", {}, constraints={"reason": "no safe local intent matched"})

    def from_provider_json(self, value: str) -> Intent:
        raw = json.loads(value)
        if raw.get("type") == "action_request":
            raw = {"goal": raw.get("goal", ""), "intent": raw["action"], "parameters": raw.get("arguments", {})}
        required = {"goal", "intent", "parameters"}
        if not required.issubset(raw) or not isinstance(raw["parameters"], dict):
            raise ValueError("invalid intent proposal")
        return Intent(raw["goal"], raw["intent"], raw["parameters"],
                      raw.get("constraints", {}), raw.get("expected_outcome", {}))