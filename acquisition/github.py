from __future__ import annotations

import requests

from acquisition.discovery import candidate_from_github


class GitHubClient:
    def __init__(self, session=None):
        self.session = session or requests.Session()

    def search(self, query: str, limit: int = 10) -> dict:
        try:
            response = self.session.get("https://api.github.com/search/repositories",
                                        params={"q": query, "per_page": min(max(1, limit), 30)}, timeout=5)
            if response.status_code == 403:
                return {"success": False, "status": "rate_limited", "candidates": []}
            response.raise_for_status()
            return {"success": True, "status": "completed",
                    "candidates": [candidate_from_github(item).as_dict() for item in response.json().get("items", [])]}
        except Exception as exc:
            return {"success": False, "status": "unavailable", "error": str(exc), "candidates": []}

    def metadata(self, owner: str, repository: str) -> dict:
        try:
            response = self.session.get(f"https://api.github.com/repos/{owner}/{repository}", timeout=5)
            response.raise_for_status()
            return {"success": True, "candidate": candidate_from_github(response.json()).as_dict()}
        except Exception as exc:
            return {"success": False, "status": "unavailable", "error": str(exc)}