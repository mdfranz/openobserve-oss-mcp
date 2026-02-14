from __future__ import annotations

import argparse
import logging
import os
import sys
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from .client import ConfigurationError, OpenObserveClient
from .server import create_mcp_server, setup_logging

logger = logging.getLogger(__name__)


def validate_url(url: str, name: str) -> str:
    """Validate that a URL is properly formatted."""
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ConfigurationError(
                f"Invalid {name}: '{url}'. Must include scheme and host (e.g., http://localhost:5080)"
            )
        return url.rstrip("/")
    except Exception as e:
        raise ConfigurationError(f"Invalid {name}: {e}") from e


def validate_port(port: int, name: str) -> int:
    """Validate that a port number is in valid range."""
    if not 1 <= port <= 65535:
        raise ConfigurationError(f"Invalid {name}: {port}. Must be between 1 and 65535")
    return port


def validate_positive_int(value: int, name: str, min_val: int = 1) -> int:
    """Validate that a value is a positive integer."""
    if value < min_val:
        raise ConfigurationError(f"Invalid {name}: {value}. Must be >= {min_val}")
    return value


def main() -> None:
    # Load environment variables from .env file
    load_dotenv()

    # Set up logging early so validation errors are logged
    log_level = os.getenv("MCP_LOG_LEVEL", "INFO").upper()
    setup_logging(log_level)

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

    # Validate configuration
    try:
        logger.info("Validating configuration...")

        # Validate OpenObserve connection parameters
        args.base_url = validate_url(args.base_url, "ZO_BASE_URL")

        if not args.org:
            raise ConfigurationError(
                "Organization name is required. Set ZO_ORG environment variable or use --org"
            )

        # Validate authentication
        has_access_key = bool(args.access_key)
        has_credentials = bool(args.email and args.password)

        if not has_access_key and not has_credentials:
            raise ConfigurationError(
                "Authentication required. Provide either:\n"
                "  1. ZO_ACCESS_KEY environment variable (recommended), or\n"
                "  2. Both ZO_ROOT_USER_EMAIL and ZO_ROOT_USER_PASSWORD\n"
                "\nSee .env.example for configuration template."
            )

        if has_credentials and not has_access_key:
            if not args.email:
                raise ConfigurationError("ZO_ROOT_USER_EMAIL is required when using email/password auth")
            if not args.password:
                raise ConfigurationError("ZO_ROOT_USER_PASSWORD is required when using email/password auth")

        # Validate timeout and limits
        args.timeout = validate_positive_int(args.timeout, "timeout", min_val=1)
        args.max_rows = validate_positive_int(args.max_rows, "max-rows", min_val=1)
        args.max_chars = validate_positive_int(args.max_chars, "max-chars", min_val=100)

        # Validate transport-specific settings
        if args.transport == "http":
            args.port = validate_port(args.port, "port")

        logger.info(
            "Configuration validated: transport=%s, base_url=%s, org=%s, auth=%s",
            args.transport,
            args.base_url,
            args.org,
            "access_key" if has_access_key else "email/password",
        )

    except ConfigurationError as e:
        logger.error("Configuration error: %s", e)
        sys.exit(1)

    # Configure HTTP auth provider
    auth_provider = None
    if args.transport == "http":
        if args.auth_disabled:
            logger.warning(
                "HTTP transport auth is DISABLED. This should only be used for local development!"
            )
            auth_provider = None
        else:
            if not args.auth_token:
                logger.error(
                    "HTTP transport requires authentication. "
                    "Set OPENOBSERVE_MCP_AUTH_TOKEN or use --auth-disabled (local/dev only)"
                )
                sys.exit(1)
            auth_provider = StaticTokenVerifier(
                tokens={args.auth_token: {"client_id": "mcp-client", "scopes": []}},
                required_scopes=[],
            )
            logger.info("HTTP transport authentication configured")

    # Create OpenObserve client
    try:
        logger.info("Initializing OpenObserve client...")
        client = OpenObserveClient(
            base_url=args.base_url,
            org=args.org,
            email=args.email,
            password=args.password,
            access_key=args.access_key,
            timeout_s=args.timeout,
        )
        logger.info("OpenObserve client initialized successfully")
    except Exception as e:
        logger.error("Failed to initialize OpenObserve client: %s", e)
        sys.exit(1)

    # Create MCP server
    try:
        logger.info("Creating MCP server...")
        mcp = create_mcp_server(
            client=client,
            max_rows=args.max_rows,
            max_chars=args.max_chars,
            auth=auth_provider,
        )
        logger.info("MCP server created successfully")
    except Exception as e:
        logger.error("Failed to create MCP server: %s", e)
        sys.exit(1)

    # Run server
    try:
        if args.transport == "http":
            logger.info("Starting HTTP server on %s:%s", args.host, args.port)
            mcp.run(
                transport="http", host=args.host, port=args.port, stateless_http=args.stateless_http
            )
        else:
            logger.info("Starting stdio transport")
            mcp.run(transport="stdio")
    except KeyboardInterrupt:
        logger.info("Server shutdown requested")
        sys.exit(0)
    except Exception as e:
        logger.error("Server error: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
