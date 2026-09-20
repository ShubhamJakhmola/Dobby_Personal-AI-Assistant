from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

from development.models import CodingAgentCapabilities, CodingAgentInfo, CodingAgentState, CodingTask


class BaseCliAdapter:
    id = "generic"
    name = "Generic CLI"
    provider = "generic"
    executable_names: tuple[str, ...] = ()
    version_args: tuple[str, ...] = ("--version",)
    help_args: tuple[str, ...] = ("--help",)
    known_invocation_styles: list[str] = []
    supports_workspace = False
    supports_headless = False
    supports_noninteractive = False
    output_format = "text"
    auth_hint = "unknown"

    def __init__(self, executable: str | None = None, timeout: float = 5):
        self.executable = executable or ""
        self.timeout = timeout
        self._last_info: CodingAgentInfo | None = None

    def _find_executable(self) -> str:
        if self.executable:
            return self.executable if shutil.which(self.executable) else ""
        for candidate in self.executable_names:
            found = shutil.which(candidate)
            if found:
                return found
        return ""

    def _safe_probe(self, executable: str, args: tuple[str, ...]) -> tuple[int | None, str, str]:
        try:
            result = subprocess.run([executable, *args], capture_output=True, text=True, timeout=self.timeout, check=False)
            return result.returncode, result.stdout[:4000], result.stderr[:4000]
        except Exception as exc:
            return None, "", str(exc)

    def _parse_version(self, stdout: str, stderr: str) -> str:
        combined = (stdout or stderr).strip().splitlines()
        return combined[0].strip()[:160] if combined else ""

    def detect(self) -> CodingAgentInfo:
        executable = self._find_executable()
        if not executable:
            info = CodingAgentInfo(self.id, self.name, self.provider, self.__class__.__name__,
                                   status=CodingAgentState.NOT_FOUND, authentication_status="not_checked")
            self._last_info = info
            return info
        code, stdout, stderr = self._safe_probe(executable, self.version_args)
        installed = code is not None
        version = self._parse_version(stdout, stderr)
        errors = [] if installed else [stderr or "version probe failed"]
        configured = installed and self._configuration_available(executable)
        available = installed and configured and not errors and self._invocation_supported(executable)
        status = CodingAgentState.AVAILABLE if available else CodingAgentState.CONFIGURED if configured else CodingAgentState.INSTALLED
        if installed and not self._invocation_supported(executable):
            status = CodingAgentState.UNAVAILABLE
            errors.append("safe noninteractive invocation contract is not known")
        capabilities = CodingAgentCapabilities(self.supports_workspace, self.supports_headless,
                                               self.supports_noninteractive, True, list(self.known_invocation_styles),
                                               limitations=[] if available else ["execution disabled until adapter has a safe invocation contract"])
        info = CodingAgentInfo(self.id, self.name, self.provider, self.__class__.__name__, executable, version,
                               status, installed, configured, available, capabilities,
                               self.supports_workspace, self.supports_headless, self.supports_noninteractive,
                               self.output_format, self.auth_hint if configured else "unknown",
                               last_health_check=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), errors=errors)
        self._last_info = info
        return info

    def _configuration_available(self, executable: str) -> bool:
        return True

    def _invocation_supported(self, executable: str) -> bool:
        return False

    def health(self) -> CodingAgentInfo:
        return self.detect()

    def capabilities(self) -> dict:
        info = self._last_info or self.detect()
        return info.capabilities.as_dict()

    def start(self, workspace: Path, task: CodingTask):
        raise NotImplementedError("adapter does not define a safe start contract")

    def send_task(self, task: CodingTask):
        raise NotImplementedError("adapter does not maintain an interactive session")

    def inspect_output(self) -> dict:
        return {"status": "not_started"}

    def stop(self) -> dict:
        return {"status": "not_running"}

    def collect_result(self):
        raise NotImplementedError("adapter has no collected result")
