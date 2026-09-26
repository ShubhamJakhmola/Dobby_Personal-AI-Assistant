"""Cross-platform local media/file playback with explicit path handling."""
from __future__ import annotations

import json
import os
import platform
import subprocess
from pathlib import Path

_MEDIA_EXTENSIONS = {
    ".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".m4v", ".mpeg", ".mpg",
    ".mp3", ".wav", ".flac", ".aac", ".m4a", ".ogg", ".opus",
}


def _resolve_path(path: str, filename: str | None = None) -> Path | None:
    raw = Path(path).expanduser()
    if raw.is_file():
        return raw.resolve()
    if raw.is_dir() and filename:
        target = filename.lower().strip()
        # Exact filename first, then a bounded recursive lookup.
        exact = raw / filename
        if exact.is_file():
            return exact.resolve()
        count = 0
        for candidate in raw.rglob("*"):
            if candidate.is_file() and candidate.name.lower() == target:
                return candidate.resolve()
            count += 1
            if count >= 5000:
                break
    return None


def _open_path(target: Path) -> tuple[bool, str]:
    system = platform.system()
    try:
        if system == "Windows":
            os.startfile(str(target))  # type: ignore[attr-defined]
        elif system == "Darwin":
            subprocess.Popen(["open", str(target)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif system == "Linux":
            subprocess.Popen(["xdg-open", str(target)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            return False, f"Unsupported operating system: {system}"
        return True, str(target)
    except Exception as exc:
        return False, str(exc)


def media_control(parameters: dict, **_) -> str:
    params = parameters or {}
    operation = str(params.get("operation", "open")).lower().strip()
    path = str(params.get("path", "")).strip()
    filename = str(params.get("filename", "")).strip() or None

    if operation not in {"open", "play"}:
        return json.dumps({"success": False, "error": "Supported operations: open, play."})
    if not path:
        return json.dumps({"success": False, "error": "A file or folder path is required."})

    target = _resolve_path(path, filename)
    if not target:
        return json.dumps({"success": False, "error_category": "file_not_found", "error": f"Media file not found: {path}"})
    if target.is_file() and target.suffix.lower() not in _MEDIA_EXTENSIONS:
        return json.dumps({"success": False, "error_category": "unsupported_media", "error": f"Not a recognised media file: {target.name}"})

    ok, detail = _open_path(target)
    if ok:
        return json.dumps({"success": True, "operation": operation, "path": str(target), "opened_with_default_app": True})
    return json.dumps({"success": False, "error_category": "open_failed", "error": detail, "path": str(target)})


TOOL = {
    "name": "media_control",
    "description": "Open or play a local audio/video file with the operating system's default media application. Use an exact file path when the user identifies a local movie or song.",
    "parameters": {"type": "OBJECT", "properties": {
        "operation": {"type": "STRING", "description": "open or play"},
        "path": {"type": "STRING", "description": "File or folder path"},
        "filename": {"type": "STRING", "description": "Optional exact filename when path is a folder"},
    }, "required": ["path"]},
    "handler": media_control,
    "risk_level": "L1",
    "reversible": True,
    "supports_verification": True,
}
