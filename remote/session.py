from __future__ import annotations

from remote.models import DeviceSession, DeviceState


class SessionManager:
    _shared_sessions: dict[str, DeviceSession] = {}

    def __init__(self):
        self._sessions = self.__class__._shared_sessions

    def open(self, device_id: str, capabilities=None) -> DeviceSession:
        session = DeviceSession(session_id=f"session-{device_id}", device_id=device_id, authenticated=True, online=True,
                               capabilities=capabilities or [], metadata={"state": DeviceState.ONLINE.value})
        self._sessions[device_id] = session
        return session

    def get(self, device_id: str) -> DeviceSession | None:
        return self._sessions.get(device_id)

    def heartbeat(self, device_id: str):
        session = self._sessions.get(device_id)
        if session is not None:
            session.online = True
            session.authenticated = True
        return session

    def close(self, device_id: str):
        session = self._sessions.get(device_id)
        if session is not None:
            session.online = False
        return session
