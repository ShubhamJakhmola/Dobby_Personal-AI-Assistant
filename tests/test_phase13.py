import os
import socket
import tempfile
import threading
import time
import unittest

from remote.authentication import DeviceAuthenticator
from remote.device_registry import DeviceRegistry, make_device_identity
from remote.models import RemoteTask
from remote.transports.tls import TLSConfig
from remote.server import DobbyCoreServer
from remote.client import LinuxRemoteClient


class PhaseThirteenTests(unittest.TestCase):
    def test_tls_status_and_cert_generation(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = TLSConfig(enabled=True, verify_cert=True, secure_mode="production")
            self.assertEqual(cfg.status(), "SECURE")
            cert, key = cfg.generate_test_material(td)
            self.assertTrue(os.path.exists(cert))
            self.assertTrue(os.path.exists(key))

    def test_loopback_remote_process_and_capabilities(self):
        with tempfile.TemporaryDirectory() as td:
            cert, key = TLSConfig(enabled=True, verify_cert=False, secure_mode="development").generate_test_material(td)
            registry = DeviceRegistry(os.path.join(td, "devices.json"))
            server = DobbyCoreServer(host="127.0.0.1", port=0, registry=registry, cert_file=cert, key_file=key, ca_file=cert, secure_mode="development")
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                time.sleep(0.5)
                client = LinuxRemoteClient(core_host="127.0.0.1", core_port=server.port, cert_file=cert, secure_mode="development",
                                          device_name="phase13-client", registry=registry)
                client.start()
                time.sleep(1.0)
                self.assertTrue(client.online)
                self.assertIn("process", client.capabilities())
                result = client.perform_task(RemoteTask("task-1", client.device_id, "process", "list", {}))
                self.assertIn("status", result)
                self.assertIn("items", result.get("payload", {}))
            finally:
                client.stop()
                server.shutdown()
                server.server_close()

    def test_enrollment_and_authentication_flow(self):
        auth = DeviceAuthenticator()
        token = auth.create_enrollment_token("dev-13")
        self.assertTrue(auth.verify_enrollment("dev-13", token.token))
        self.assertFalse(auth.verify_enrollment("dev-13", token.token))

    def test_l3_terminal_stays_blocked(self):
        from security.policy import classify
        decision = classify("terminal_execute", {"command": ["sudo", "systemctl", "restart", "nginx"]})
        self.assertEqual(decision.level, 3)
        self.assertTrue(decision.requires_confirmation)


if __name__ == "__main__":
    unittest.main()
