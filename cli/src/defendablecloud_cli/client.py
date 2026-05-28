"""Thin httpx wrapper for the DefendableCloud API.

Surfaces API errors as CLIError with the detail from the JSON response — the
operator sees `API 409: a human must approve before a receipt is issued` not
a raw httpx traceback.
"""
from __future__ import annotations

import json as _json
from pathlib import Path
from typing import Any

import httpx

from . import __version__
from .credentials import api_base_url, stored_token
from .errors import AuthError, CLIError


class Client:
    def __init__(self, *, base_url: str | None = None, token: str | None = None, timeout: float = 30.0):
        self.base_url = api_base_url(base_url)
        self.token = token if token is not None else stored_token()
        self.http = httpx.Client(
            base_url=self.base_url,
            headers=self._headers(),
            timeout=timeout,
        )

    def _headers(self) -> dict[str, str]:
        h = {
            "Accept": "application/json",
            "User-Agent": f"defendable-cli/{__version__}",
        }
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    # ── verbs ────────────────────────────────────────────────────────────────

    def get(self, path: str, *, params: dict[str, Any] | None = None, auth_required: bool = True) -> Any:
        return self._do("GET", path, params=params, auth_required=auth_required)

    def post(
        self,
        path: str,
        *,
        json: Any | None = None,
        files: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        auth_required: bool = True,
    ) -> Any:
        return self._do("POST", path, json=json, files=files, data=data, auth_required=auth_required)

    def patch(self, path: str, *, json: Any | None = None) -> Any:
        return self._do("PATCH", path, json=json)

    def delete(self, path: str) -> Any:
        return self._do("DELETE", path)

    def upload(self, path: str, *, file_path: Path, label: str | None = None) -> Any:
        with file_path.open("rb") as fh:
            files = {"file": (file_path.name, fh, "application/octet-stream")}
            data = {"label": label} if label else None
            return self.post(path, files=files, data=data)

    # ── core ─────────────────────────────────────────────────────────────────

    def _do(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: Any | None = None,
        files: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        auth_required: bool = True,
    ) -> Any:
        if auth_required and not self.token:
            raise AuthError()

        try:
            r = self.http.request(method, path, params=params, json=json, files=files, data=data)
        except httpx.HTTPError as e:
            raise CLIError(f"network error: {e}")

        if r.status_code == 401:
            raise AuthError("API rejected the credential — token expired? run `defendable auth login`")
        if r.status_code >= 400:
            detail = self._error_detail(r)
            raise CLIError(f"API {r.status_code}: {detail}")

        if r.status_code == 204 or not r.content:
            return None
        try:
            return r.json()
        except _json.JSONDecodeError:
            return r.text

    @staticmethod
    def _error_detail(r: httpx.Response) -> str:
        try:
            body = r.json()
            return body.get("detail") or body.get("error") or _json.dumps(body)
        except _json.JSONDecodeError:
            return r.text or r.reason_phrase
