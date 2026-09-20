from __future__ import annotations

from pathlib import Path


def validate_path(target: str | Path, workspace_root: str | Path) -> bool:
    root = Path(workspace_root).resolve()
    candidate = Path(target).resolve()
    try:
        candidate.relative_to(root)
        return True
    except ValueError:
        return False
