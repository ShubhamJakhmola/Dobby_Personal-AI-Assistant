from __future__ import annotations

try:
    import pyautogui
except Exception:
    pyautogui = None


def _require():
    if pyautogui is None:
        raise RuntimeError("mouse backend unavailable: install pyautogui")


def position() -> dict:
    _require()
    point = pyautogui.position()
    return {"x": point.x, "y": point.y}


def move(x: int, y: int, duration: float = 0.0) -> dict:
    _require()
    pyautogui.moveTo(int(x), int(y), duration=max(0.0, min(float(duration), 5.0)))
    return position()


def click(x: int | None = None, y: int | None = None, button: str = "left", clicks: int = 1) -> dict:
    _require()
    if x is not None and y is not None:
        pyautogui.click(int(x), int(y), button=button, clicks=int(clicks))
    else:
        pyautogui.click(button=button, clicks=int(clicks))
    return {"clicked": True, "button": button, "clicks": int(clicks), **position()}