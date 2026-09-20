from __future__ import annotations

import platform
import shlex
import shutil
import subprocess
from pathlib import Path

_MARKER = "# dobby-task:"


class CronScheduler:
    """User crontab adapter; it never invokes a shell and never uses root."""

    def _read(self) -> list[str]:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, check=False)
        if result.returncode not in (0, 1):
            raise RuntimeError(result.stderr.strip() or "could not read crontab")
        return result.stdout.splitlines() if result.returncode == 0 else []

    def _write(self, lines: list[str]) -> None:
        result = subprocess.run(["crontab", "-"], input="\n".join(lines).rstrip() + "\n",
                                capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "could not install crontab")

    def list(self) -> dict[str, dict]:
        if platform.system() != "Linux" or not shutil.which("crontab"):
            return {}
        entries = {}
        for line in self._read():
            if _MARKER not in line:
                continue
            body, _, name = line.partition(_MARKER)
            fields = body.strip().split(maxsplit=5)
            if len(fields) < 6:
                continue
            entries[name.strip()] = {
                "name": name.strip(),
                "schedule": " ".join(fields[:5]),
                "command": shlex.split(fields[5]),
                "enabled": not line.lstrip().startswith("#"),
            }
        return entries

    def verify(self, name: str, schedule: str | None = None, command: list[str] | None = None) -> bool:
        entry = self.list().get(name)
        return bool(entry and (schedule is None or entry["schedule"] == schedule)
                    and (command is None or entry["command"] == command))