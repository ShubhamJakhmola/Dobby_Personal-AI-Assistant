from __future__ import annotations

import io
import threading
import re
import subprocess
import platform
from datetime import datetime, timezone

from computer.models import FrameResult, Monitor

try:
    import mss
    import mss.tools
except ImportError:
    mss = None

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    import numpy as np
except ImportError:
    np = None


def detect_backends() -> list[str]:
    return ["mss"] if platform.system() == "Linux" and mss is not None else []


def select_backend() -> str | None:
    return detect_backends()[0] if detect_backends() else None


def _open_capture():
    factory = getattr(mss, "mss", mss)
    return factory()


def _monitor(raw: dict, index: int, primary: bool = False) -> Monitor:
    return Monitor(index, int(raw.get("left", 0)), int(raw.get("top", 0)),
                   int(raw.get("width", 0)), int(raw.get("height", 0)), primary)


def _primary_geometry() -> tuple[int, int, int, int] | None:
    """Ask X11 for the primary geometry when xrandr is available."""
    try:
        output = subprocess.run(["xrandr", "--query"], capture_output=True, text=True,
                                timeout=2, check=False).stdout
        match = re.search(r"connected\s+primary\b.*?\s(\d+)x(\d+)\+(\-?\d+)\+(\-?\d+)", output)
        return tuple(map(int, match.groups())) if match else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def list_monitors() -> list[Monitor]:
    if mss is None:
        return []
    with _open_capture() as capture:
        raw_monitors = list(capture.monitors[1:])
        primary_geometry = _primary_geometry()
        monitors = [_monitor(raw, index) for index, raw in enumerate(raw_monitors)]
        if primary_geometry:
            width, height, left, top = primary_geometry
            for monitor in monitors:
                if (monitor.width, monitor.height, monitor.left, monitor.top) == (width, height, left, top):
                    monitor.primary = True
        if monitors and not any(item.primary for item in monitors):
            monitors[0].primary = True
        return monitors


def get_monitor(index: int) -> Monitor | None:
    return next((item for item in list_monitors() if item.index == int(index)), None)


def get_primary_monitor() -> Monitor | None:
    monitors = list_monitors()
    return next((item for item in monitors if item.primary), monitors[0] if monitors else None)


def _diagnose(png: bytes, width: int, height: int, backend: str, monitor: int) -> FrameResult:
    if not png or width <= 0 or height <= 0:
        return FrameResult(False, monitor, width, height, "image/png", backend,
                           error_category="invalid_frame", error="empty or invalid frame")
    if Image is None or np is None:
        return FrameResult(True, monitor, width, height, "image/png", backend, frame=png)
    try:
        pixels = np.asarray(Image.open(io.BytesIO(png)).convert("RGB"))
        near_black = float(np.mean(np.all(pixels <= 8, axis=2)))
        variance = float(np.var(pixels))
        black = near_black >= 0.995 and variance < 4.0
        return FrameResult(True, monitor, width, height, "image/png", backend,
                           black_frame=black, near_black_ratio=near_black,
                           pixel_variance=variance, frame=png,
                           error_category="black_frame_detected" if black else None,
                           error="captured frame is nearly black" if black else None)
    except Exception as exc:
        return FrameResult(False, monitor, width, height, "image/png", backend,
                           error_category="invalid_frame", error=str(exc))


def capture_monitor(index: int, timeout: float = 5.0) -> FrameResult:
    backend = select_backend()
    if backend is None:
        return FrameResult(False, index, backend="", error_category="backend_unavailable", error="no screen backend available")
    monitor = get_monitor(index)
    if monitor is None:
        return FrameResult(False, index, backend=backend, error_category="monitor_not_found", error="monitor not found")
    result: list[FrameResult] = []
    finished = threading.Event()

    def capture() -> None:
        try:
            with _open_capture() as capture_context:
                shot = capture_context.grab({"left": monitor.left, "top": monitor.top,
                                             "width": monitor.width, "height": monitor.height})
                png = mss.tools.to_png(shot.rgb, shot.size)
                result.append(_diagnose(png, monitor.width, monitor.height, backend, index))
        except PermissionError as exc:
            result.append(FrameResult(False, index, backend=backend, error_category="permission_denied", error=str(exc)))
        except Exception as exc:
            result.append(FrameResult(False, index, backend=backend, error_category="screen_capture_failed", error=str(exc)))
        finally:
            finished.set()

    threading.Thread(target=capture, daemon=True).start()
    if not finished.wait(timeout):
        return FrameResult(False, index, backend=backend, error_category="capture_timeout", error="screen capture timed out")
    return result[0]


def capture_all_monitors(timeout: float = 5.0) -> list[FrameResult]:
    return [capture_monitor(monitor.index, timeout) for monitor in list_monitors()]