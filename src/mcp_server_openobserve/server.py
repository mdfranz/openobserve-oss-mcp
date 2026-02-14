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

    def _search_sql_impl(
        sql: str,
        hours: int | None = None,
        start_micros: int | None = None,
        end_micros: int | None = None,
        size: int = 100,
        offset: int = 0,
    ) -> Any:
        logger.info(
            "_search_sql_impl request: sql=%s hours=%s start_micros=%s end_micros=%s size=%s offset=%s",
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
            "_search_sql_impl executing: org=%s start=%s end=%s size=%s offset=%s",
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
            logger.info("_search_sql_impl completed successfully")
            return _apply_max_chars(result, max_chars)
        except (APIError, AuthenticationError, OpenObserveConnectionError) as e:
            logger.error("_search_sql_impl failed: %s", e)
            raise
        except Exception as e:
            logger.error("_search_sql_impl unexpected error: %s", e, exc_info=True)
            raise

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
        return _search_sql_impl(
            sql=sql,
            hours=hours,
            start_micros=start_micros,
            end_micros=end_micros,
            size=size,
            offset=offset,
        )

    @mcp.tool(
        name="search_logs",
        title="Search Logs",
        description="Search logs in a stream using a full-text query string.",
        annotations=read_only_annotations,
    )
    def search_logs(
        query: str,
        stream: str = "default",
        hours: int = 1,
        size: int = 100,
        offset: int = 0,
    ) -> Any:
        logger.info("search_logs request: query=%s stream=%s hours=%s", query, stream, hours)

        # Simple escaping for single quotes to prevent basic SQL errors
        safe_query = query.replace("'", "''")

        # Construct SQL for full-text search
        # Using match_all which searches across all fields or fields configured for full text
        sql = f"SELECT * FROM {stream} WHERE match_all('{safe_query}')"

        return _search_sql_impl(
            sql=sql,
            hours=hours,
            size=size,
            offset=offset,
        )

    @mcp.tool(
        name="get_log_volume",
        title="Get Log Volume",
        description="Get the volume of logs (count) over time (histogram).",
        annotations=read_only_annotations,
    )
    def get_log_volume(
        stream: str = "default",
        hours: int = 24,
        interval: str = "1 hour",
    ) -> Any:
        logger.info(
            "get_log_volume request: stream=%s hours=%s interval=%s", stream, hours, interval
        )

        safe_interval = interval.replace("'", "''")

        sql = f"SELECT histogram(_timestamp, '{safe_interval}') AS key, COUNT(*) AS num FROM {stream} GROUP BY key ORDER BY key"

        return _search_sql_impl(
            sql=sql,
            hours=hours,
            size=1000,
            offset=0,
        )

    @mcp.tool(
        name="get_stream_schema",
        title="Get Stream Schema",
        description="Get the schema (field names and types) for a specific stream.",
        annotations=read_only_annotations,
    )
    def get_stream_schema(stream: str) -> Any:
        logger.info("get_stream_schema executing: stream=%s", stream)
        try:
            result = client.get_stream_schema(stream)
            logger.info("get_stream_schema completed successfully")
            return _apply_max_chars(result, max_chars)
        except (APIError, AuthenticationError, OpenObserveConnectionError) as e:
            logger.error("get_stream_schema failed: %s", e)
            raise
        except Exception as e:
            logger.error("get_stream_schema unexpected error: %s", e, exc_info=True)
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

    @mcp.prompt()
    def investigate_errors(stream: str = "default", hours: int = 1) -> str:
        return f"""
        Please investigate the '{stream}' stream for errors over the last {hours} hours.

        1. First, use get_stream_schema('{stream}') to understand the available fields.
        2. Then, use search_sql with a query like "SELECT * FROM {stream} WHERE level='error' OR message LIKE '%error%'"
        3. Summarize any critical issues found.
        """

    @mcp.prompt()
    def summarize_activity(stream: str = "default") -> str:
        return f"""
        Please provide a summary of activity for the '{stream}' stream.

        1. Use get_log_volume(stream='{stream}', hours=24) to see the traffic patterns.
        2. Use search_sql to sample recent logs: "SELECT * FROM {stream} LIMIT 10"
        3. Describe the type of data being logged and any notable volume spikes.
        """

    @mcp.prompt()
    def generate_sql_query(goal: str, stream: str = "default") -> str:
        return f"""
        I need to write a SQL query for the '{stream}' stream to achieve this goal: {goal}

        Please:
        1. Inspect the schema using get_stream_schema('{stream}').
        2. Construct a valid SQL query compatible with OpenObserve (which uses a syntax similar to PostgreSQL/MySQL but with some specific functions).
        3. Explain the query.
        """

    @mcp.prompt()
    def smart_search(query: str) -> str:
        return f"""
        The user wants to find: "{query}"

        1. List the available streams using list_streams().
        2. If the query is simple text, use search_logs().
        3. If the query requires filtering by specific fields or aggregations, use search_sql().
        """

    return mcp
