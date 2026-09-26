import json
import os
import tempfile
import threading
import time
import unittest

from remote.authentication import DeviceAuthenticator
from remote.client import LinuxRemoteClient
from remote.credential_store import CredentialStore
from remote.device_registry import DeviceRegistry, make_device_identity
from remote.models import RemoteTask, RemoteTaskResult
from remote.server import DobbyCoreServer
from remote.task_queue import TaskQueue
from remote.transports.tls import TLSConfig


class PhaseFourteenTests(unittest.TestCase):
    def test_tls_verification_modes_and_cert_material(self):
        config = TLSConfig(enabled=True, verify_cert=True, secure_mode="production")
        self.assertEqual(config.status(), "SECURE")
        self.assertEqual(config.mode, "production")
        with tempfile.TemporaryDirectory() as td:
            cert, key, ca = config.generate_test_material_with_ca(td)
            self.assertTrue(os.path.exists(cert))
            self.assertTrue(os.path.exists(key))
            self.assertTrue(os.path.exists(ca))

    def test_credential_store_and_identity_persistence(self):
        with tempfile.TemporaryDirectory() as td:
            store = CredentialStore(path=os.path.join(td, "creds.json"), development_mode=True)
            identity = make_device_identity("persisted-linux", "linux")
            store.save_identity(identity)
            restored = store.load_identity(identity.device_id)
            self.assertEqual(restored["device_id"], identity.device_id)
            self.assertEqual(store.state(), "DEVELOPMENT_ONLY")

    def test_registry_revocation_persistence_and_routing(self):
        with tempfile.TemporaryDirectory() as td:
            registry = DeviceRegistry(os.path.join(td, "devices.json"))
            a = make_device_identity("device-a", "linux")
            b = make_device_identity("device-b", "linux")
            registry.enroll(a)
            registry.enroll(b)
            registry.update_capabilities(a.device_id, [{"id": "process"}, {"id": "filesystem"}])
            registry.update_capabilities(b.device_id, [{"id": "filesystem"}])
            registry._devices[a.device_id]["state"] = "ONLINE"
            registry._devices[b.device_id]["state"] = "ONLINE"
            registry.revoke(a.device_id)
            registry2 = DeviceRegistry(os.path.join(td, "devices.json"))
            self.assertEqual(registry2.get(a.device_id)["state"], "REVOKED")
            self.assertIsNone(registry2.select_for_task(RemoteTask("t", a.device_id, "process", "list", {})))

    def test_challenge_authentication_and_invalid_signature(self):
        auth = DeviceAuthenticator()
        challenge = auth.create_challenge("dev-14")
        good = auth.sign_challenge(challenge, "dev-14")
        self.assertTrue(auth.verify_challenge("dev-14", challenge, good))
        self.assertFalse(auth.verify_challenge("dev-14", challenge, "not-valid"))

    def test_session_heartbeat_and_degraded_state(self):
        queue = TaskQueue(max_pending_tasks=2)
        session = {"session_id": "s1", "device_id": "d1", "last_activity": time.time(), "state": "ONLINE"}
        self.assertEqual(queue.state_for(session), "ONLINE")
        session["last_activity"] = time.time() - 80
        self.assertEqual(queue.state_for(session), "DEGRADED")
        session["last_activity"] = time.time() - 3600
        self.assertEqual(queue.state_for(session), "OFFLINE")

    def test_task_queue_and_duplicate_task_protection(self):
        queue = TaskQueue(max_pending_tasks=2)
        first = RemoteTask("task-1", "device-1", "process", "list", {})
        second = RemoteTask("task-2", "device-1", "process", "list", {})
        queue.enqueue(first)
        queue.enqueue(second)
        self.assertEqual(len(queue.pending()), 2)
        self.assertTrue(queue.duplicate(first.task_id))
        self.assertTrue(queue.add_result(first.task_id, RemoteTaskResult(first.task_id, first.device_id, status="COMPLETED")))

    def test_path_traversal_and_symlink_safety(self):
        from remote.file_security import validate_path
        safe = validate_path("/tmp/workspace/demo", "/tmp/workspace")
        self.assertTrue(safe)
        self.assertFalse(validate_path("/tmp/other/passwd", "/tmp/workspace"))
        self.assertFalse(validate_path("../escape", "/tmp/workspace"))

    def test_multi_device_routing_and_deterministic_selection(self):
        with tempfile.TemporaryDirectory() as td:
            registry = DeviceRegistry(os.path.join(td, "devices.json"))
            a = make_device_identity("linux-a", "linux")
            b = make_device_identity("linux-b", "linux")
            registry.enroll(a)
            registry.enroll(b)
            registry.update_capabilities(a.device_id, [{"id": "process", "version": "1"}, {"id": "filesystem", "version": "1"}])
            registry.update_capabilities(b.device_id, [{"id": "filesystem", "version": "1"}])
            registry._devices[a.device_id]["state"] = "ONLINE"
            registry._devices[b.device_id]["state"] = "ONLINE"
            selected = registry.select_for_task(RemoteTask("t", "target", "process", "list", {}), preferred_platform="linux")
            self.assertEqual(selected["device_id"], a.device_id)

    def test_loopback_tls_server_client_and_security_mode(self):
        with tempfile.TemporaryDirectory() as td:
            cert, key, ca = TLSConfig(enabled=True, verify_cert=True, secure_mode="production").generate_test_material_with_ca(td)
            registry = DeviceRegistry(os.path.join(td, "devices.json"))
            server = DobbyCoreServer(host="127.0.0.1", port=0, registry=registry, cert_file=cert, key_file=key, ca_file=ca, secure_mode="production")
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                time.sleep(0.5)
                client = LinuxRemoteClient(core_host="127.0.0.1", core_port=server.port, cert_file=cert, secure_mode="production", device_name="client-loopback", registry=registry)
                response = client.start()
                self.assertEqual(response["status"], "accepted")
                task = RemoteTask("loopback-1", client.device_id, "process", "list", {})
                result = client.perform_task(task)
                self.assertIn("status", result)
            finally:
                client.stop()
                server.shutdown()
                server.server_close()


if __name__ == "__main__":
    unittest.main()
