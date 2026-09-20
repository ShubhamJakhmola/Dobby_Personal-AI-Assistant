"""Local network/process discovery capability."""
from __future__ import annotations

import json
import psutil


def port_process(parameters: dict, **_) -> str:
    port = int((parameters or {}).get("port", 0))
    if not 1 <= port <= 65535:
        return json.dumps({"success": False, "status": "failed", "error_category": "invalid_arguments", "error": "port must be 1-65535"})
    matches = []
    for connection in psutil.net_connections(kind="inet"):
        if connection.laddr and connection.laddr.port == port:
            matches.append({"pid": connection.pid, "status": connection.status,
                            "address": f"{connection.laddr.ip}:{connection.laddr.port}"})
    return json.dumps({"success": True, "status": "completed", "port": port,
                       "processes": matches, "query_completed": True, "verified": True})


TOOL = {"name": "network_port_process", "description": "Inspect which local process is using a TCP port.",
        "network_access": False, "supports_verification": True,
        "parameters": {"type": "OBJECT", "properties": {"port": {"type": "NUMBER"}}, "required": ["port"]},
        "handler": port_process}