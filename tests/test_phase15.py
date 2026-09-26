import unittest

from remote.network_config import RemoteNetworkConfig, detect_network_scope


class PhaseFifteenTests(unittest.TestCase):
    def test_detect_network_scope_for_loopback(self):
        self.assertEqual(detect_network_scope("127.0.0.1"), "LOCAL_LOOPBACK")
        self.assertEqual(detect_network_scope("localhost"), "LOCAL_LOOPBACK")

    def test_detect_network_scope_for_lan(self):
        self.assertEqual(detect_network_scope("0.0.0.0"), "LAN")
        self.assertEqual(detect_network_scope("192.168.1.50"), "LAN")

    def test_remote_network_config_defaults(self):
        config = RemoteNetworkConfig()
        self.assertEqual(config.bind_host, "127.0.0.1")
        self.assertEqual(config.network_scope, "LOCAL_LOOPBACK")
        self.assertEqual(config.tls_mode, "development")

    def test_remote_network_config_accepts_lan_binding(self):
        config = RemoteNetworkConfig(bind_host="0.0.0.0", port=8765, tls_mode="production")
        self.assertEqual(config.bind_host, "0.0.0.0")
        self.assertEqual(config.network_scope, "LAN")
        self.assertEqual(config.tls_mode, "production")


if __name__ == "__main__":
    unittest.main()
