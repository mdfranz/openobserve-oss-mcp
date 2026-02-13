from __future__ import annotations

import json
import logging
import time
from typing import Any, Iterable

from fastmcp import FastMCP

from .client import APIError, AuthenticationError, OpenObserveClient, OpenObserveConnectionError

logger = logging.getLogger(__name__)


def setup_logging(level: str = "INFO") -> None:
    """Configure logging for the MCP server.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
               Can be set via MCP_LOG_LEVEL environment variable.
    """
    # Map string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    root_logger = logging.getLogger()

    # Only configure if not already configured
    if not root_logger.handlers:
        # Use a more detailed format for DEBUG level
        if numeric_level == logging.DEBUG:
            log_format = "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s"
        else:
            log_format = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"

        logging.basicConfig(
            level=numeric_level,
            format=log_format,
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    # Set level for our loggers
    for logger_name in ("mcp_server_openobserve", "__main__"):
        logging.getLogger(logger_name).setLevel(numeric_level)

    logger.info("Logging configured: level=%s", level.upper())
    logger.debug("Debug logging is enabled")


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
    logger.info("Creating MCP server with max_rows=%d, max_chars=%d", max_rows, max_chars)

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
        logger.info(
            "search_sql request: sql=%s hours=%s start_micros=%s end_micros=%s size=%s offset=%s",
            sql,
            hours,
            start_micros,
            end_micros,
            size,
            offset,
        )

        # Validate SQL input
        if not sql or not sql.strip():
            raise ValueError("SQL query cannot be empty")

        # Calculate time range
        now = int(time.time() * 1_000_000)
        if hours is not None:
            if hours <= 0:
                raise ValueError(f"hours must be positive, got {hours}")
            start_micros = now - hours * 60 * 60 * 1_000_000
            end_micros = now + 60 * 60 * 1_000_000

        start = start_micros if start_micros is not None else (now - 24 * 60 * 60 * 1_000_000)
        end = end_micros if end_micros is not None else (now + 60 * 60 * 1_000_000)

        # Validate and apply limits
        effective_size = max(1, int(size))
        if max_rows > 0:
            effective_size = min(effective_size, max_rows)
        effective_offset = max(0, int(offset))

        logger.info(
            "search_sql executing: org=%s start=%s end=%s size=%s offset=%s",
            client.org,
            start,
            end,
            effective_size,
            effective_offset,
        )
        logger.debug("SQL query: %s", sql)

        try:
            result = client.search(
                sql=sql,
                start_time_micros=start,
                end_time_micros=end,
                size=effective_size,
                offset=effective_offset,
            )
            logger.info("search_sql completed successfully")
            return _apply_max_chars(result, max_chars)
        except (APIError, AuthenticationError, OpenObserveConnectionError) as e:
            logger.error("search_sql failed: %s", e)
            raise
        except Exception as e:
            logger.error("search_sql unexpected error: %s", e, exc_info=True)
            raise

    @mcp.tool(
        name="list_streams",
        title="List Streams",
        description="List streams for the configured OpenObserve org.",
        annotations=read_only_annotations,
    )
    def list_streams() -> Any:
        logger.info("list_streams executing: org=%s", client.org)
        try:
            result = client.list_streams()
            logger.info("list_streams completed successfully")
            return _apply_max_chars(result, max_chars)
        except (APIError, AuthenticationError, OpenObserveConnectionError) as e:
            logger.error("list_streams failed: %s", e)
            raise
        except Exception as e:
            logger.error("list_streams unexpected error: %s", e, exc_info=True)
            raise

    @mcp.tool(
        name="get_api",
        title="GET API",
        description=(
            "GET a limited OpenObserve API path. Allowed paths: `healthz`, `api/{org}/...`."
        ),
        annotations=open_world_annotations,
    )
    def get_api(path: str, param: list[str] | None = None) -> Any:
        logger.debug("get_api request: path=%s param=%s", path, param)

        try:
            cleaned = _normalize_api_path(path)
        except ValueError as e:
            logger.error("Invalid API path: %s - %s", path, e)
            raise

        allowed_prefix = f"api/{client.org}/"
        if cleaned != "healthz" and not cleaned.startswith(allowed_prefix):
            error_msg = f"Path must be 'healthz' or start with '{allowed_prefix}', got '{cleaned}'"
            logger.error(error_msg)
            raise ValueError(error_msg)

        try:
            params = _parse_kv_pairs(param or [])
        except ValueError as e:
            logger.error("Invalid parameters: %s", e)
            raise

        logger.info("get_api executing: path=%s params=%s", cleaned, params or None)

        try:
            result = client.get(cleaned, params=params or None)
            logger.info("get_api completed successfully")
            return _apply_max_chars(result, max_chars)
        except (APIError, AuthenticationError, OpenObserveConnectionError) as e:
            logger.error("get_api failed: %s", e)
            raise
        except Exception as e:
            logger.error("get_api unexpected error: %s", e, exc_info=True)
            raise

    return mcp
