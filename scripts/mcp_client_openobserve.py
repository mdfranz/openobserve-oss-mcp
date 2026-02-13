#!/usr/bin/env python3
"""
Smoke-test MCP client for the OpenObserve MCP server using Pydantic AI's MCP client.

Based on: https://ai.pydantic.dev/mcp/client/

Examples:
  # HTTP (server already running)
  export OPENOBSERVE_MCP_AUTH_TOKEN="dev-token"   # unless server started with --auth-disabled
  python3 scripts/mcp_client_openobserve.py http --url http://127.0.0.1:8001/mcp

  # stdio (spawns the server via uv from this repo)
  export ZO_BASE_URL=http://127.0.0.1:5080
  export ZO_ORG=default
  export ZO_ACCESS_KEY="..."
  python3 scripts/mcp_client_openobserve.py stdio

  # Run a search query (SQL must reference a stream/table)
  python3 scripts/mcp_client_openobserve.py http --url http://127.0.0.1:8001/mcp \
    --sql "select * from nginx limit 5" --hours 24
"""

from __future__ import annotations

import argparse
import asyncio
import os
from typing import Any

from pydantic_ai.mcp import MCPServerStdio, MCPServerStreamableHTTP


async def _print_tools(server: Any) -> None:
    tools = await server.list_tools()
    print("Tools:")
    for tool in tools:
        print(f"- {tool.name}")


async def _run_smoke_calls(server: Any, sql: str, hours: int, size: int) -> None:
    print("\nCalling list_streams …")
    streams = await server.direct_call_tool("list_streams", {})
    print(streams)

    if sql:
        print("\nCalling search_sql …")
        result = await server.direct_call_tool(
            "search_sql",
            {
                "sql": sql,
                "hours": hours,
                "size": size,
                "offset": 0,
            },
        )
        print(result)


async def _run_http(
    url: str, token: str | None, sql: str, hours: int, size: int
) -> None:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    server = MCPServerStreamableHTTP(url, headers=headers or None)
    async with server:
        await _print_tools(server)
        await _run_smoke_calls(server, sql=sql, hours=hours, size=size)


async def _run_stdio(
    command: str,
    args: list[str],
    sql: str,
    hours: int,
    size: int,
) -> None:
    # NOTE: MCPServerStdio does not inherit env vars by default.
    server = MCPServerStdio(command, args=args, env=dict(os.environ))
    async with server:
        await _print_tools(server)
        await _run_smoke_calls(server, sql=sql, hours=hours, size=size)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Smoke-test client for mcp-server-openobserve"
    )
    parser.add_argument(
        "--sql", default="", help="SQL query (must reference a stream/table)"
    )
    parser.add_argument("--hours", type=int, default=1)
    parser.add_argument("--size", type=int, default=10)

    sub = parser.add_subparsers(dest="transport", required=True)

    http_cmd = sub.add_parser(
        "http", help="Connect to an already running HTTP MCP server"
    )
    http_cmd.add_argument("--url", default="http://127.0.0.1:8001/mcp")
    http_cmd.add_argument("--token", default=os.getenv("OPENOBSERVE_MCP_AUTH_TOKEN"))

    stdio_cmd = sub.add_parser("stdio", help="Spawn the MCP server over stdio")
    stdio_cmd.add_argument("--command", default="uv")
    stdio_cmd.add_argument(
        "--args",
        nargs="*",
        default=[
            "run",
            "mcp-server-openobserve",
            "--transport",
            "stdio",
        ],
    )

    args = parser.parse_args()

    if args.transport == "http":
        asyncio.run(
            _run_http(
                url=args.url,
                token=args.token,
                sql=args.sql,
                hours=args.hours,
                size=args.size,
            )
        )
    else:
        asyncio.run(
            _run_stdio(
                command=args.command,
                args=args.args,
                sql=args.sql,
                hours=args.hours,
                size=args.size,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
