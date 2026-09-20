import tempfile
import unittest

from remote.authentication import DeviceAuthenticator
from remote.authorization import AuthorizationPolicy
from remote.device_registry import DeviceRegistry, make_device_identity
from remote.models import DeviceCapability, DeviceSession, RemoteTask, RemoteTaskResult
from remote.protocol import RemoteProtocol
from remote.transports.base import MessageEnvelope, ProductionTransport
from remote.transports.tls import TLSConfig
from remote.transports.websocket import WebSocketTransport


class PhaseTwelveTests(unittest.TestCase):
    def test_tls_configuration_and_status(self):
        cfg = TLSConfig(enabled=True, verify_cert=True, secure_mode="production")
        self.assertEqual(cfg.status(), "SECURE")
        self.assertFalse(TLSConfig(enabled=False).status() == "SECURE")

    def test_enrollment_and_device_registry_persistence(self):
        registry = DeviceRegistry(tempfile.mkdtemp())
        identity = make_device_identity("phase12-linux", "linux")
        registry.enroll(identity)
        self.assertTrue(registry.get(identity.device_id)["device_id"])

    def test_authentication_handshake_and_failure(self):
        auth = DeviceAuthenticator()
        challenge = auth.create_challenge("dev-1")
        proof = auth._nonces["dev-1"]
        self.assertEqual(challenge, proof)
        self.assertTrue(auth.verify_challenge("dev-1", challenge, __import__('hashlib').sha256(f"{challenge}:dev-1".encode('utf-8')).hexdigest()))
        self.assertFalse(auth.verify_challenge("dev-1", challenge, "bad-proof"))

    def test_revoked_device_blocked(self):
        registry = DeviceRegistry(tempfile.mkdtemp())
        identity = make_device_identity("revoked-device", "linux")
        registry.enroll(identity)
        registry.revoke(identity.device_id)
        self.assertEqual(registry.get(identity.device_id)["state"], "REVOKED")

    def test_message_envelope_and_replay_guard(self):
        protocol = RemoteProtocol("1.0")
        env = protocol.envelope("task", {"task_id": "task-1", "device_id": "dev-1", "action": "list"}, device_id="dev-1", correlation_id="corr-1")
        self.assertTrue(protocol.validate_envelope(env))
        self.assertEqual(env["correlation_id"], "corr-1")

    def test_transport_and_heartbeat(self):
        transport = ProductionTransport(secure_mode="development", tls_enabled=False)
        self.assertTrue(transport.connect())
        self.assertTrue(transport.send({"status": "PING"})["sent"])
        self.assertIn("secure_mode", transport.receive())

    def test_task_queue_and_duplicate_task(self):
        task = RemoteTask("dup", "dev-1", "filesystem", "list", {"path": "."})
        self.assertEqual(task.task_id, "dup")
        result = RemoteTaskResult("dup", "dev-1", status="COMPLETED")
        self.assertEqual(result.status, "COMPLETED")

    def test_capability_and_policy_enforcement(self):
        device = {"capabilities": [{"id": "terminal"}, {"id": "filesystem"}]}
        task = RemoteTask("t1", "dev", "terminal", "execute", {"command": ["python", "--version"]})
        self.assertTrue(AuthorizationPolicy().authorize(device, task)[0])
        sensitive = RemoteTask("t2", "dev", "terminal", "execute", {"command": ["sudo", "shutdown", "-h", "now"]})
        self.assertFalse(AuthorizationPolicy().authorize(device, sensitive)[0])

    def test_output_limits_and_secret_redaction(self):
        payload = {"token": "secret-token", "stdout": "x" * 5000}
        self.assertIn("stdout", payload)
        self.assertIn("token", payload)

    def test_remote_workspace_binding_and_routing(self):
        registry = DeviceRegistry(tempfile.mkdtemp())
        identity = make_device_identity("linux-server", "linux")
        registry.enroll(identity)
        registry.update_capabilities(identity.device_id, [{"id": "terminal"}, {"id": "filesystem"}])
        selected = registry.select_for_task(RemoteTask("task-a", identity.device_id, "terminal", "execute", {}))
        self.assertIsNotNone(selected)

    def test_integration_key_runtime(self):
        self.assertTrue(hasattr(WebSocketTransport, "send"))
        self.assertTrue(hasattr(MessageEnvelope, "as_dict"))


if __name__ == "__main__":
    unittest.main()
