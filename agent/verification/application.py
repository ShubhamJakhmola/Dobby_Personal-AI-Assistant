from __future__ import annotations

from agent.verification.process import verify_process_running


def verify_application_running(application: str):
    return verify_process_running(name=application)