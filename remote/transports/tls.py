from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class TLSConfig:
    enabled: bool = False
    verify_cert: bool = False
    cert_file: str = ""
    key_file: str = ""
    ca_file: str = ""
    secure_mode: str = "development"
    mode: str = "development"

    def __post_init__(self):
        if self.mode == "development" and self.secure_mode in {"production", "local_test"}:
            self.mode = self.secure_mode
        elif not self.mode:
            self.mode = self.secure_mode

    def status(self) -> str:
        return "SECURE" if self.enabled and self.verify_cert else "DEVELOPMENT / INSECURE"

    def generate_test_material(self, directory: str) -> tuple[str, str]:
        cert_path, key_path, _ = self.generate_test_material_with_ca(directory)
        return cert_path, key_path

    def generate_test_material_with_ca(self, directory: str) -> tuple[str, str, str]:
        if not os.path.isdir(directory):
            os.makedirs(directory, exist_ok=True)
        cert_path = os.path.join(directory, "test-cert.pem")
        key_path = os.path.join(directory, "test-key.pem")
        ca_path = os.path.join(directory, "test-ca.pem")
        cert_text = """-----BEGIN CERTIFICATE-----
MIIB2TCCAYCgAwIBAgIUKBvQkS1xk1dZ6s1n9l5d2g6mXwM0wDQYJKoZIhvcNAQEL
BQAwEjEQMA4GA1UEAwwFZGV2LWNlcnQwHhcNMjYwOTIwMDAwMDAwWhcNMzcwOTIw
MDAwMDAwWjATMBEGA1UEAwwKMTI3LjAuMC4xWTATBgNVBAMMDE1vY2tDZXJ0MB0G
A1UdDgQWBBRdc9YmpEOQqKv0fC3dG3AqNCnuxsQvGqEwDAYDVR0lA0MB8GA1UdEwQY
MBaAFD4f9D4xv8A5pD8gH8UQm0Qn1L8Q52J0s+GFPfJ3JpNy4uV9Yk3k6QOcM9J0s+GFPfJ3JpNy4uV9Yk3k6QOcM9P0N3vDtIu1offdM5y2/e9gQbs2bYx8KqGtDWF2dYQvPk1v8Ww8xY7KrcxUy7P1gT0h0l
wQpcL7a+8uVj8Y5s6vVSrft6Nh9M+MC9eZJdLz/G1v43D6mezAtNw3m/KtGJbOA=
-----END CERTIFICATE-----
"""
        key_text = """-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQDh3lUQeY06U3jZ
D4dCd2FMYwMq0MZfTyhKplk3HvlheQ5uM8G7aW9tE5MIJtdPkk9VREXG9xn4pk1M9
xjo7OGEw3WnAtx7i+JkH2I0b9z2em0Xr9P5sDEgWRz2kZ0JqlO4HkVxIgNLWH5W+d
309Rlq8S4r2sL+JYj+40Jm6jO4kCsUIE2R0+9YbEqnPls9dCMWqtwByc2nG9cK9mZ
QW3GmKf4h0y8h6NkE1luv2N7HlONVgP2QbniJuV0ocQ9N7i7wSdLhR6g3oGSQ04v
Vb6sM8r4ao1rVhG2eFUQn3zjuo6l4NhZdcqZL1o7yb7J8LnlwJeL8Vc0zLn5f5p9x
JfNKaEwsZ8W3YYFuG9R4lY2a1sHoj3W79un7V6bD3ma8R1zDuFPrnxZl+0fQ0aoiN
sF5a4a0Wfn86d7u2pC9p5mN3A6eWAQjvJ+2g6H3l9iWjS9xSlw4J1vV+0nJ4t4w0w
S59bHbQ3uAIOG11EJ3dLXQ9Sm7ZCTQv2lM3PV2F4vkc9E2wA1XnqC2F1DZZh3xQ6p0
IhN4UINtZq+5kU7j9ys9DrdK7zS7A3WcsuP2YwB1T5NqNw0M+zP1L2o2iL0OvcvE
qJ+J9Cwz6wQpP3yvAAoTIRpuWlPjTg15z2bycY8uJHS9O4HkQ7+z7v1iv4k0q8h7
KccJw6b4dVY31A==
-----END PRIVATE KEY-----
"""
        ca_text = """-----BEGIN CERTIFICATE-----
MIICAjCCAgOgAwIBAgIUF4qv4NwC3c9Jw7d6k9jy7D0gYUwDQYJKoZIhvcNAQEL
BQAwEjEQMA4GA1UEAwwFZGV2LWNlcnQwHhcNMjYwOTIwMDAwMDAwWhcNMzcwOTIw
MDAwMDAwWjATMBEGA1UEAwwKMTI3LjAuMC4xWTATBgNVBAMMDE1vY2tDZXJ0MB0G
A1UdDgQWBBRdc9YmpEOQqKv0fC3dG3AqNCnuxsQvGqEwDAYDVR0lA0MB8GA1UdEwQY
MBaAFD4f9D4xv8A5pD8gH8UQm0Qn1L8Q52J0s+GFPfJ3JpNy4uV9Yk3k6QOcM9P0
N3vDtIu1offdM5y2/e9gQbs2bYx8KqGtDWF2dYQvPk1v8Ww8xY7KrcxUy7P1gT0h0l
wQpcL7a+8uVj8Y5s6vVSrft6Nh9M+MC9eZJdLz/G1v43D6mezAtNw3m/KtGJbOA=
-----END CERTIFICATE-----
"""
        with open(cert_path, "w", encoding="utf-8") as cert_file:
            cert_file.write(cert_text)
        with open(key_path, "w", encoding="utf-8") as key_file:
            key_file.write(key_text)
        with open(ca_path, "w", encoding="utf-8") as ca_file:
            ca_file.write(ca_text)
        return cert_path, key_path, ca_path
