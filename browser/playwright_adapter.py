from __future__ import annotations


class PlaywrightAdapter:
    def __init__(self):
        try:
            from playwright.async_api import async_playwright  # noqa: F401
        except ImportError as exc:
            self.error = str(exc)
        else:
            self.error = ""

    def status(self) -> dict:
        return {"available": not bool(self.error),
                "error_category": None if not self.error else "browser_automation_unavailable",
                "error": self.error or None}

    def open(self, url: str) -> dict:
        status = self.status()
        if not status["available"]:
            return {"success": False, **status}
        return {"success": False, "error_category": "not_implemented", "error": "browser adapter requires an async session"}