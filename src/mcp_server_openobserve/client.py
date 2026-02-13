from __future__ import annotations

import os
from typing import Any

import requests


class OpenObserveClient:
    def __init__(
        self,
        base_url: str | None = None,
        org: str | None = None,
        email: str | None = None,
        password: str | None = None,
        access_key: str | None = None,
        timeout_s: int = 30,
    ) -> None:
        self.base_url = (base_url or os.getenv("ZO_BASE_URL", "http://127.0.0.1:5080")).rstrip("/")
        self.org = org or os.getenv("ZO_ORG", "default")
        self.email = email or os.getenv("ZO_ROOT_USER_EMAIL")
        self.password = password or os.getenv("ZO_ROOT_USER_PASSWORD")
        self.access_key = access_key or os.getenv("ZO_ACCESS_KEY")
        self.timeout_s = timeout_s

        if not self.access_key and not (self.email and self.password):
            raise ValueError("Provide access_key or email/password via args or env vars")

    def _auth_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.access_key:
            headers["Authorization"] = f"Basic {self.access_key}"
        return headers

    def _request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = dict(self._auth_headers())
        headers.update(kwargs.pop("headers", {}))
        auth = None if self.access_key else (self.email, self.password)
        response = requests.request(
            method,
            url,
            headers=headers,
            auth=auth,
            timeout=self.timeout_s,
            **kwargs,
        )
        if not response.ok:
            raise RuntimeError(f"HTTP {response.status_code}: {response.text}")
        return response

    def search(
        self,
        sql: str,
        start_time_micros: int,
        end_time_micros: int,
        size: int,
        offset: int,
    ) -> dict[str, Any]:
        payload = {
            "query": {
                "sql": sql,
                "from": offset,
                "size": size,
                "start_time": start_time_micros,
                "end_time": end_time_micros,
            }
        }
        return self._request("POST", f"api/{self.org}/_search", json=payload).json()

    def list_streams(self) -> Any:
        return self._request("GET", f"api/{self.org}/streams").json()

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request("GET", path, params=params).json()
