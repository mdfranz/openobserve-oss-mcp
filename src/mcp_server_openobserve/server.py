from __future__ import annotations

import json
import time
from typing import Any, Iterable

from fastmcp import FastMCP

from .client import OpenObserveClient


def _parse_kv_pairs(pairs: Iterable[str]) -> dict[str, str]:
    params: dict[str, str] = {}
    for item in pairs:
        if "=" not in item:
            raise ValueError(f"Expected key=value pair, got: {item}")
        key, value = item.split("=", 1)
        params[key] = value
    return params


def _apply_max_chars(payload: Any, max_chars: int) -> Any:
    if max_chars <= 0:
        return payload
    encoded = json.dumps(payload, ensure_ascii=False, default=str)
    if len(encoded) <= max_chars:
        return payload
    preview = encoded[:max_chars]
    if isinstance(payload, dict):
        return {
            "truncated": True,
            "max_chars": max_chars,
            "keys": sorted(payload.keys()),
            "preview": preview,
        }
    return {
        "truncated": True,
        "max_chars": max_chars,
        "preview": preview,
    }


def _normalize_api_path(path: str) -> str:
    cleaned = path.strip()
    if cleaned.startswith("http://") or cleaned.startswith("https://"):
        raise ValueError("Only relative API paths are allowed (no scheme/host)")
    cleaned = cleaned.lstrip("/")
    if ".." in cleaned.split("/"):
        raise ValueError("Path traversal is not allowed")
    return cleaned


def create_mcp_server(
    *,
    client: OpenObserveClient,
    max_rows: int = 1000,
    max_chars: int = 50_000,
    auth: Any | None = None,
) -> FastMCP:
    mcp = FastMCP(
        name="mcp-server-openobserve",
        instructions=(
            "Query OpenObserve using SQL via the `search_sql` tool. "
            "Use `list_streams` to discover available streams. "
            "All tools are read-only."
        ),
        auth=auth,
    )

    read_only_annotations = {
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": False,
    }

    open_world_annotations = {
        "readOnlyHint": True,
        "destructiveHint": False,
        "openWorldHint": True,
    }

    @mcp.tool(
        name="search_sql",
        title="Search SQL",
        description="Run an OpenObserve SQL query via /api/{org}/_search.",
        annotations=read_only_annotations,
    )
    def search_sql(
        sql: str,
        hours: int | None = None,
        start_micros: int | None = None,
        end_micros: int | None = None,
        size: int = 100,
        offset: int = 0,
    ) -> Any:
        now = int(time.time() * 1_000_000)
        if hours is not None:
            start_micros = now - hours * 60 * 60 * 1_000_000
            end_micros = now + 60 * 60 * 1_000_000

        start = start_micros if start_micros is not None else (now - 24 * 60 * 60 * 1_000_000)
        end = end_micros if end_micros is not None else (now + 60 * 60 * 1_000_000)

        effective_size = max(1, int(size))
        if max_rows > 0:
            effective_size = min(effective_size, max_rows)
        effective_offset = max(0, int(offset))

        result = client.search(
            sql=sql,
            start_time_micros=start,
            end_time_micros=end,
            size=effective_size,
            offset=effective_offset,
        )
        return _apply_max_chars(result, max_chars)

    @mcp.tool(
        name="list_streams",
        title="List Streams",
        description="List streams for the configured OpenObserve org.",
        annotations=read_only_annotations,
    )
    def list_streams() -> Any:
        result = client.list_streams()
        return _apply_max_chars(result, max_chars)

    @mcp.tool(
        name="get_api",
        title="GET API",
        description=(
            "GET a limited OpenObserve API path. Allowed paths: `healthz`, `api/{org}/...`."
        ),
        annotations=open_world_annotations,
    )
    def get_api(path: str, param: list[str] | None = None) -> Any:
        cleaned = _normalize_api_path(path)
        allowed_prefix = f"api/{client.org}/"
        if cleaned != "healthz" and not cleaned.startswith(allowed_prefix):
            raise ValueError(f"Path must be healthz or start with {allowed_prefix}")

        params = _parse_kv_pairs(param or [])
        result = client.get(cleaned, params=params or None)
        return _apply_max_chars(result, max_chars)

    return mcp
