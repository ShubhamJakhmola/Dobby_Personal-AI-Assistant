from __future__ import annotations

from core import gemini


class GeminiProvider:
    """Adapter retaining the existing Gemini ladder as Dobby's active brain."""

    def text(self, prompt: str, *, system: str = "", timeout_ms: int = 10000) -> str:
        config = {"system_instruction": system} if system else None
        response = gemini.call(prompt, tier=gemini.SMART, config=config, timeout_ms=timeout_ms)
        if response is None:
            raise RuntimeError("Gemini did not return a response")
        return str(response.text or "").strip()