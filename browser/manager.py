from __future__ import annotations

from browser.playwright_adapter import PlaywrightAdapter


class BrowserManager:
    def __init__(self, adapter=None):
        self.adapter = adapter or PlaywrightAdapter()

    def status(self) -> dict:
        return self.adapter.status()

    def open(self, url: str) -> dict:
        return self.adapter.open(url)