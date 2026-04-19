"""Thin httpx wrapper for the ClickUp v2 REST API.

Auth: personal token in `Authorization` header (no `Bearer` prefix).
Rate limit: 100 req/min on Free/Unlimited plans. Back off on 429 using X-RateLimit-Reset.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = REPO_ROOT / "config.json"
BASE_URL = "https://api.clickup.com/api/v2"


def load_token(config_path: Path = CONFIG_PATH) -> str:
    data = json.loads(config_path.read_text())
    token = data.get("CLICKUP_API_TOKEN")
    if not token or token.startswith("pk_XXXXX"):
        raise RuntimeError(
            f"CLICKUP_API_TOKEN missing or placeholder in {config_path}. "
            "Set your personal token (Settings → Apps → API Token in ClickUp)."
        )
    return token


def load_config(config_path: Path = CONFIG_PATH) -> dict[str, Any]:
    return json.loads(config_path.read_text())


class ClickUpError(RuntimeError):
    def __init__(self, method: str, path: str, status: int, body: str) -> None:
        super().__init__(f"ClickUp {method} {path} -> {status}: {body[:500]}")
        self.status = status
        self.body = body


class ClickUpClient:
    def __init__(self, token: str | None = None, base_url: str = BASE_URL, timeout: float = 30.0) -> None:
        self.token = token or load_token()
        self.base_url = base_url
        self._http = httpx.Client(
            base_url=base_url,
            headers={"Authorization": self.token},
            timeout=timeout,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "ClickUpClient":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json_body: Any | None = None,
        files: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> Any:
        for attempt in range(4):
            resp = self._http.request(
                method,
                path,
                params=params,
                json=json_body if files is None else None,
                files=files,
                data=data,
            )
            if resp.status_code == 429:
                reset = int(resp.headers.get("X-RateLimit-Reset", "0"))
                wait = max(1, reset - int(time.time())) if reset else (2 ** attempt)
                time.sleep(min(wait, 60))
                continue
            if resp.status_code >= 400:
                raise ClickUpError(method, path, resp.status_code, resp.text)
            if resp.status_code == 204 or not resp.content:
                return None
            ctype = resp.headers.get("content-type", "")
            if "json" in ctype:
                return resp.json()
            return resp.text
        raise ClickUpError(method, path, 429, "rate limit retries exhausted")

    def get(self, path: str, **params: Any) -> Any:
        return self._request("GET", path, params=params or None)

    def post(self, path: str, json_body: Any | None = None, **params: Any) -> Any:
        return self._request("POST", path, json_body=json_body, params=params or None)

    def put(self, path: str, json_body: Any | None = None, **params: Any) -> Any:
        return self._request("PUT", path, json_body=json_body, params=params or None)

    def delete(self, path: str, **params: Any) -> Any:
        return self._request("DELETE", path, params=params or None)

    def post_multipart(self, path: str, files: dict[str, Any], data: dict[str, Any] | None = None) -> Any:
        return self._request("POST", path, files=files, data=data)
