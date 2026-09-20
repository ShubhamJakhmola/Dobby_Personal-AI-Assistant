from __future__ import annotations

import json
import sys

from clients.base import ClientRuntime


def main() -> int:
    command = sys.argv[1] if len(sys.argv) > 1 else "status"
    runtime = ClientRuntime()
    if command == "status":
        print(json.dumps(runtime.status_report(), indent=2))
        return 0
    if command == "capabilities":
        print(json.dumps({"capabilities": runtime.capabilities}, indent=2))
        return 0
    if command == "enroll":
        print(json.dumps({"status": "ENROLLING", "note": "enrollment is explicit and requires a secure device identity flow"}, indent=2))
        return 0
    print("Usage: python dobby-client.py status|capabilities|enroll", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
