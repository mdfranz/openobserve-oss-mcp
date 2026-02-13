from __future__ import annotations

import argparse
import os

from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from .client import OpenObserveClient
from .server import create_mcp_server


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenObserve MCP server (read/query only)")
    parser.add_argument(
        "--transport",
        choices=("stdio", "http"),
        default=os.getenv("MCP_TRANSPORT", "stdio"),
    )
    parser.add_argument("--host", default=os.getenv("MCP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MCP_PORT", "8001")))
    parser.add_argument("--stateless-http", action="store_true", default=False)

    parser.add_argument("--base-url", default=os.getenv("ZO_BASE_URL", "http://127.0.0.1:5080"))
    parser.add_argument("--org", default=os.getenv("ZO_ORG", "default"))
    parser.add_argument("--email", default=os.getenv("ZO_ROOT_USER_EMAIL"))
    parser.add_argument("--password", default=os.getenv("ZO_ROOT_USER_PASSWORD"))
    parser.add_argument("--access-key", default=os.getenv("ZO_ACCESS_KEY"))
    parser.add_argument("--timeout", type=int, default=int(os.getenv("ZO_TIMEOUT", "30")))

    parser.add_argument("--max-rows", type=int, default=int(os.getenv("MCP_MAX_ROWS", "1000")))
    parser.add_argument("--max-chars", type=int, default=int(os.getenv("MCP_MAX_CHARS", "50000")))

    parser.add_argument("--auth-token", default=os.getenv("OPENOBSERVE_MCP_AUTH_TOKEN"))
    parser.add_argument("--auth-disabled", action="store_true", default=False)

    args = parser.parse_args()

    auth_provider = None
    if args.transport == "http":
        if args.auth_disabled:
            auth_provider = None
        else:
            if not args.auth_token:
                raise SystemExit(
                    "HTTP transport requires auth by default. Set OPENOBSERVE_MCP_AUTH_TOKEN "
                    "or pass --auth-disabled (local/dev only)."
                )
            auth_provider = StaticTokenVerifier(
                tokens={args.auth_token: {"client_id": "mcp-client", "scopes": []}},
                required_scopes=[],
            )

    client = OpenObserveClient(
        base_url=args.base_url,
        org=args.org,
        email=args.email,
        password=args.password,
        access_key=args.access_key,
        timeout_s=args.timeout,
    )

    mcp = create_mcp_server(
        client=client,
        max_rows=args.max_rows,
        max_chars=args.max_chars,
        auth=auth_provider,
    )

    if args.transport == "http":
        mcp.run(
            transport="http", host=args.host, port=args.port, stateless_http=args.stateless_http
        )
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
