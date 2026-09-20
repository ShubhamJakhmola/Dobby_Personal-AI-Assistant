from __future__ import annotations

import json
import sys

from computer.diagnostics import collect_environment, format_report, run_live_validation
from memory.commands import handle as memory_command


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "diagnostics"
    if command == "diagnostics":
        print(format_report(collect_environment()))
        return 0
    if command == "validate-linux":
        print(json.dumps(run_live_validation(), indent=2))
        return 0
    if command == "memory" and len(sys.argv) > 2:
        result = memory_command("memory " + " ".join(sys.argv[2:]))
        print(result or "Unknown memory command.")
        return 0 if result else 2
    if command == "context" and len(sys.argv) > 1:
        print(memory_command("context show") or "No context available.")
        return 0
    print("Usage: python -m dobby diagnostics | validate-linux | memory <command> | context", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())