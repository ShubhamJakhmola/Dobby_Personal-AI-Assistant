from __future__ import annotations

try:
    import pyautogui
except ImportError:
    pyautogui = None


def _require():
    if pyautogui is None:
        raise RuntimeError("keyboard backend unavailable: install pyautogui")


def type_text(text: str, interval: float = 0.02) -> dict:
    _require()
    pyautogui.write(str(text), interval=max(0.0, min(float(interval), 1.0)))
    return {"typed": True, "characters": len(str(text))}


def press(key: str) -> dict:
    _require()
    pyautogui.press(str(key))
    return {"pressed": str(key)}


def hotkey(keys: list[str] | str) -> dict:
    _require()
    values = keys.split("+") if isinstance(keys, str) else list(keys)
    pyautogui.hotkey(*[str(item).lower().strip() for item in values])
    return {"pressed": values}