from __future__ import annotations

try:
    import pyperclip
except ImportError:
    pyperclip = None


def _require():
    if pyperclip is None:
        raise RuntimeError("clipboard backend unavailable: install pyperclip and a Linux clipboard provider")


def get() -> dict:
    _require()
    value = pyperclip.paste()
    return {"text": value, "length": len(value)}


def set_text(text: str) -> dict:
    _require()
    pyperclip.copy(str(text))
    return {"set": True, "length": len(str(text))}


def clear() -> dict:
    _require()
    pyperclip.copy("")
    return {"cleared": True}