from __future__ import annotations

import json
from pathlib import Path


def inspect_dependencies(root: str | Path) -> dict:
    root = Path(root)
    result = {"runtime": "unknown", "package_manager": "unknown", "files": [], "dependencies": [], "lockfiles": []}
    requirements = root / "requirements.txt"
    pyproject = root / "pyproject.toml"
    package = root / "package.json"
    if requirements.exists():
        result.update(runtime="python", package_manager="pip")
        result["files"].append("requirements.txt")
        result["dependencies"] = [line.strip() for line in requirements.read_text(encoding="utf-8", errors="replace").splitlines() if line.strip() and not line.startswith("#")]
    if pyproject.exists():
        result.update(runtime="python", package_manager="pyproject")
        result["files"].append("pyproject.toml")
    if package.exists():
        result.update(runtime="node", package_manager="npm")
        result["files"].append("package.json")
        try: result["dependencies"] = list(json.loads(package.read_text(encoding="utf-8")).get("dependencies", {}).keys())
        except json.JSONDecodeError: result["parse_error"] = True
    for name in ("poetry.lock", "uv.lock", "package-lock.json", "pnpm-lock.yaml", "yarn.lock"):
        if (root / name).exists(): result["lockfiles"].append(name)
    return result