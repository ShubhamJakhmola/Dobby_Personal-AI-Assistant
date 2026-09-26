from __future__ import annotations

from dataclasses import dataclass


def detect_network_scope(host: str) -> str:
    host_value = (host or "").strip().lower()
    if host_value in {"127.0.0.1", "localhost", "::1"}:
        return "LOCAL_LOOPBACK"
    if host_value == "0.0.0.0":
        return "LAN"
    if host_value.startswith("192.168.") or host_value.startswith("10.") or host_value.startswith("172."):
        return "LAN"
    if host_value.startswith("0."):
        return "LAN"
    return "LAN" if host_value else "LOCAL_LOOPBACK"


@dataclass
class RemoteNetworkConfig:
    bind_host: str = "127.0.0.1"
    port: int = 8765
    tls_mode: str = "development"
    cert_file: str = ""
    key_file: str = ""
    ca_file: str = ""
    verify_client: bool = False
    network_scope: str = "LOCAL_LOOPBACK"

    def __post_init__(self):
        self.network_scope = detect_network_scope(self.bind_host)

    def as_dict(self) -> dict:
        return {
            "bind_host": self.bind_host,
            "port": self.port,
            "tls_mode": self.tls_mode,
            "network_scope": self.network_scope,
            "verify_client": self.verify_client,
        }
