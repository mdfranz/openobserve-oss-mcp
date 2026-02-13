#!/usr/bin/env python3
"""Simple OpenObserve API client for local usage.

Usage examples:
  python src/mcp_server_openobserve/oo_client.py search --sql "select * from nginx limit 5"
  python src/mcp_server_openobserve/oo_client.py search --sql "select * from nginx limit 5" --format yaml
  python src/mcp_server_openobserve/oo_client.py ingest --stream nginx --file sample.json
  python src/mcp_server_openobserve/oo_client.py get /api/default/streams
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, Iterable

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
        self.base_url = (
            base_url or os.getenv("ZO_BASE_URL", "http://127.0.0.1:5080")
        ).rstrip("/")
        self.org = org or os.getenv("ZO_ORG", "default")
        self.email = email or os.getenv("ZO_ROOT_USER_EMAIL")
        self.password = password or os.getenv("ZO_ROOT_USER_PASSWORD")
        self.access_key = access_key or os.getenv("ZO_ACCESS_KEY")
        self.timeout_s = timeout_s

        if not self.access_key and not (self.email and self.password):
            raise ValueError(
                "Provide access_key or email/password via args or env vars"
            )

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

    def ingest_json(self, stream: str, records: list[dict[str, Any]]) -> dict[str, Any]:
        if not isinstance(records, list):
            raise ValueError("records must be a list of objects")
        path = f"api/{self.org}/{stream}/_json"
        return self._request("POST", path, json=records).json()

    def search(
        self,
        sql: str,
        start_time_micros: int | None = None,
        end_time_micros: int | None = None,
        size: int = 1000,
        offset: int = 0,
    ) -> dict[str, Any]:
        now = int(time.time() * 1_000_000)
        start_time = start_time_micros or (now - 24 * 60 * 60 * 1_000_000)
        end_time = end_time_micros or (now + 60 * 60 * 1_000_000)
        payload = {
            "query": {
                "sql": sql,
                "from": offset,
                "size": size,
                "start_time": start_time,
                "end_time": end_time,
            }
        }
        return self._request("POST", f"api/{self.org}/_search", json=payload).json()

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request("GET", path, params=params).json()


def _load_records(path: str | None, inline_json: str | None) -> list[dict[str, Any]]:
    if path:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    elif inline_json:
        data = json.loads(inline_json)
    else:
        raise ValueError("Provide --file or --data")

    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    raise ValueError("JSON must be an object or list of objects")


def _parse_kv_pairs(pairs: Iterable[str]) -> dict[str, str]:
    params: dict[str, str] = {}
    for item in pairs:
        if "=" not in item:
            raise ValueError(f"Expected key=value pair, got: {item}")
        key, value = item.split("=", 1)
        params[key] = value
    return params


def main() -> int:
    parser = argparse.ArgumentParser(description="Simple OpenObserve API client")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--org", default=None)
    parser.add_argument("--email", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--access-key", default=None)
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument(
        "--format",
        choices=("json", "yaml"),
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "--yaml",
        dest="format",
        action="store_const",
        const="yaml",
        help="Alias for --format yaml",
    )
    parser.add_argument("--pretty", action="store_true", default=True)
    parser.add_argument("--no-pretty", dest="pretty", action="store_false")

    sub = parser.add_subparsers(dest="command", required=True)

    search_cmd = sub.add_parser("search", help="Run a SQL query")
    search_cmd.add_argument("--sql", required=True)
    search_cmd.add_argument("--size", type=int, default=1000)
    search_cmd.add_argument("--offset", type=int, default=0)
    search_cmd.add_argument("--start-micros", type=int, default=None)
    search_cmd.add_argument("--end-micros", type=int, default=None)
    search_cmd.add_argument(
        "--hours", type=int, default=None, help="Lookback window in hours"
    )

    ingest_cmd = sub.add_parser("ingest", help="Ingest JSON records")
    ingest_cmd.add_argument("--stream", required=True)
    ingest_cmd.add_argument("--file", default=None)
    ingest_cmd.add_argument("--data", default=None, help="Inline JSON string")

    get_cmd = sub.add_parser("get", help="GET a raw API path")
    get_cmd.add_argument("path")
    get_cmd.add_argument("--param", action="append", default=[], help="key=value")

    sub.add_parser("list-streams", help="List streams for the org")
    sub.add_parser("ping", help="Health check")

    args = parser.parse_args()

    client = OpenObserveClient(
        base_url=args.base_url,
        org=args.org,
        email=args.email,
        password=args.password,
        access_key=args.access_key,
        timeout_s=args.timeout,
    )

    try:
        if args.command == "search":
            start_micros = args.start_micros
            end_micros = args.end_micros
            if args.hours is not None:
                now = int(time.time() * 1_000_000)
                start_micros = now - args.hours * 60 * 60 * 1_000_000
                end_micros = now + 60 * 60 * 1_000_000
            result = client.search(
                sql=args.sql,
                start_time_micros=start_micros,
                end_time_micros=end_micros,
                size=args.size,
                offset=args.offset,
            )
        elif args.command == "ingest":
            records = _load_records(args.file, args.data)
            result = client.ingest_json(args.stream, records)
        elif args.command == "get":
            params = _parse_kv_pairs(args.param)
            result = client.get(args.path, params=params or None)
        elif args.command == "list-streams":
            result = client.get(f"api/{client.org}/streams")
        elif args.command == "ping":
            result = client.get("healthz")
        else:
            raise ValueError(f"Unknown command: {args.command}")

        if args.format == "yaml":
            try:
                import yaml  # type: ignore[import-not-found]
            except ImportError as exc:
                raise RuntimeError(
                    "YAML output requires PyYAML. Install with: pip install pyyaml"
                ) from exc
            print(
                yaml.safe_dump(
                    result,
                    sort_keys=True,
                    default_flow_style=(not args.pretty),
                ).rstrip()
            )
        else:
            if args.pretty:
                print(json.dumps(result, indent=2, sort_keys=True))
            else:
                print(json.dumps(result))
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
