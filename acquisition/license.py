from __future__ import annotations

import re

KNOWN = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "GPL-2.0", "GPL-3.0", "LGPL-2.1", "LGPL-3.0", "MPL-2.0", "ISC"}


def inspect_license(files: dict[str, str] | None = None, spdx_id: str = "") -> dict:
    files = files or {}
    detected = spdx_id or ""
    file_name = ""
    if not detected:
        for name, text in files.items():
            upper = text.upper()
            if "MIT LICENSE" in upper or re.search(r"\bMIT\b", upper): detected, file_name = "MIT", name
            elif "APACHE LICENSE" in upper: detected, file_name = "Apache-2.0", name
            elif "GNU GENERAL PUBLIC LICENSE" in upper: detected, file_name = "GPL", name
            if detected: break
    return {"license_detected": bool(detected), "license_identifier": detected,
            "license_file": file_name, "license_known": detected in KNOWN,
            "status": "REVIEW_REQUIRED" if detected in {"GPL", "GPL-2.0", "GPL-3.0"} else "observed"}