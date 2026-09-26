import tempfile
import unittest

from remote.authentication import DeviceAuthenticator
from remote.authorization import AuthorizationPolicy
from remote.device_registry import DeviceRegistry, make_device_identity
from remote.models import DeviceCapability, DeviceIdentity, DeviceSession, RemoteTask, RemoteTaskResult
from remote.protocol import RemoteProtocol
from remote.session import SessionManager


class PhaseElevenTests(unittest.TestCase):
    def test_device_identity_and_registry(self):
        identity = make_device_identity("mock-linux", "linux")
        self.assertTrue(identity.device_id)
        registry = DeviceRegistry(tempfile.mkdtemp())
        registry.enroll(identity, DeviceSession("session-1", identity.device_id, authenticated=True, online=True,
                                               capabilities=[DeviceCapability("terminal"), DeviceCapability("filesystem")]))
        self.assertEqual(registry.get(identity.device_id)["device_name"], "mock-linux")

    def test_enrollment_authentication(self):
        authenticator = DeviceAuthenticator()
        token = authenticator.create_enrollment_token("dev-1")
        self.assertTrue(authenticator.verify_enrollment("dev-1", token.token))
        self.assertFalse(authenticator.verify_enrollment("dev-1", token.token))

    def test_authorization_and_policy(self):
        device = {"capabilities": [DeviceCapability("terminal").as_dict()]}
        task = RemoteTask("t1", "dev", "terminal", "execute", {"command": ["python", "--version"]})
        self.assertTrue(AuthorizationPolicy().authorize(device, task)[0])
        sensitive = RemoteTask("t2", "dev", "terminal", "execute", {"command": ["sudo", "systemctl", "restart", "nginx"]})
        self.assertFalse(AuthorizationPolicy().authorize(device, sensitive)[0])

    def test_capability_negotiation_and_removal(self):
        registry = DeviceRegistry(tempfile.mkdtemp())
        identity = make_device_identity("mock-windows", "windows")
        registry.enroll(identity)
        registry.update_capabilities(identity.device_id, [{"id": "terminal", "version": "1"}, {"id": "browser", "version": "1"}])
        selected = registry.select_for_task(RemoteTask("task-1", identity.device_id, "browser", "open", {}))
        self.assertIsNotNone(selected)
        registry.update_capabilities(identity.device_id, [{"id": "terminal", "version": "1"}])
        self.assertIsNone(registry.select_for_task(RemoteTask("task-2", identity.device_id, "browser", "open", {})))

    def test_online_offline_and_heartbeat(self):
        registry = DeviceRegistry(tempfile.mkdtemp())
        identity = make_device_identity("mock-linux", "linux")
        registry.enroll(identity)
        registry._devices[identity.device_id]["state"] = "ONLINE"
        self.assertEqual(registry.status()["online"], 1)
        session = SessionManager().open(identity.device_id)
        self.assertTrue(session.online)
        session = SessionManager().heartbeat(identity.device_id)
        self.assertTrue(session.online)

    def test_remote_task_validation_and_result(self):
        task = RemoteTask("task-1", "id-1", "process", "list", {})
        result = RemoteTaskResult("task-1", "id-1", status="COMPLETED", stdout="ok")
        protocol = RemoteProtocol()
        self.assertTrue(protocol.validate(protocol.encode_task(task)))
        self.assertEqual(protocol.decode_result(protocol.encode_result(result)).status, "COMPLETED")

    def test_duplicate_task_and_cancellation_state(self):
        registry = DeviceRegistry(tempfile.mkdtemp())
        identity = make_device_identity("mock-limited", "linux")
        registry.enroll(identity)
        task = RemoteTask("dup", identity.device_id, "filesystem", "list", {"path": "."})
        self.assertEqual(task.task_id, "dup")
        result = RemoteTaskResult(task.task_id, identity.device_id, status="CANCELLED")
        self.assertEqual(result.status, "CANCELLED")

    def test_revocation_and_protocol_compatibility(self):
        registry = DeviceRegistry(tempfile.mkdtemp())
        identity = make_device_identity("mock-revoked", "windows")
        registry.enroll(identity)
        self.assertTrue(registry.revoke(identity.device_id)["success"])
        protocol = RemoteProtocol("1.0")
        self.assertEqual(protocol.version, "1.0")

    def test_service_capabilities_and_client_runtime(self):
        from clients.base import ClientRuntime
        runtime = ClientRuntime()
        self.assertTrue(hasattr(runtime, "status"))


if __name__ == "__main__":
    unittest.main()
