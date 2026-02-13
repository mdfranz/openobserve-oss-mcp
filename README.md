# OpenObserve MCP Server

An MCP (Model Context Protocol) server that enables AI assistants to query and explore your OpenObserve observability data. This server provides read-only access to logs, metrics, and traces stored in OpenObserve, allowing LLMs to help you analyze and troubleshoot your systems.

## Features

- **Read-only access** - Safe querying without data modification
- **SQL queries** - Run custom SQL queries against your observability data
- **Stream management** - List and explore available data streams
- **Flexible deployment** - Supports both stdio and HTTP transports
- **Multiple clients** - Works with Claude Desktop, Gemini CLI, Codex, and more

## Prerequisites

- **Python 3.10 or higher**
- **uv** package manager - [Install uv](https://docs.astral.sh/uv/getting-started/installation/)
- **OpenObserve instance** running locally or remotely
- **OpenObserve credentials** - Email/password or access token with read permissions

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/openobserve-oss-mcp.git
cd openobserve-oss-mcp
```

2. Install dependencies:
```bash
uv sync
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your OpenObserve credentials
```

Required environment variables:
- `ZO_BASE_URL` - Your OpenObserve instance URL (e.g., `http://127.0.0.1:5080`)
- `ZO_ORG` - OpenObserve organization name (usually `default`)
- `ZO_ACCESS_KEY` - Basic Auth credentials in format `user@example.com:password` (base64-encoded) or access token

To generate `ZO_ACCESS_KEY` from your OpenObserve credentials:
```bash
echo -n "your-email@example.com:your-password" | base64
```

## Running the Server

### Stdio Transport (Recommended for AI assistants)

```bash
uv run mcp-server-openobserve --transport stdio
```

### HTTP Transport

HTTP with authentication (production):

```bash
export OPENOBSERVE_MCP_AUTH_TOKEN="your-secure-token"
uv run mcp-server-openobserve --transport http --host 127.0.0.1 --port 8001
```

HTTP without auth (local development only):

```bash
uv run mcp-server-openobserve --transport http --host 127.0.0.1 --port 8001 --auth-disabled
```

### Output Limits

Control response sizes with these options:
- `--max-rows` - Maximum number of rows returned from SQL queries (default: 100)
- `--max-chars` - Maximum characters in response payload (default: 50000)

## Available Tools

The MCP server exposes these tools to AI assistants:

### `search_sql`
Run SQL queries against your OpenObserve data.

**Parameters:**
- `sql_query` (string, required) - SQL query to execute
- `start_time` (int, optional) - Start timestamp in milliseconds
- `end_time` (int, optional) - End timestamp in milliseconds

**Example usage:**
```sql
SELECT * FROM nginx_logs WHERE status >= 400 LIMIT 10
```

### `list_streams`
List all available streams (tables) in your OpenObserve organization.

**Returns:** Array of stream objects with names, types, and metadata.

### `get_api`
Make GET requests to specific OpenObserve API endpoints (limited subset for safety).

**Parameters:**
- `endpoint` (string, required) - API endpoint path

**Allowed endpoints:**
- `/api/{org}/streams`
- `/api/{org}/stream/{stream}`
- Organization and user info endpoints

## Client Configuration

### Claude Desktop

Edit your `claude_desktop_config.json` (Settings → Developer → Edit Config):

```json
{
  "mcpServers": {
    "openobserve": {
      "type": "stdio",
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/openobserve-oss-mcp",
        "run",
        "mcp-server-openobserve",
        "--transport",
        "stdio"
      ],
      "env": {
        "ZO_BASE_URL": "http://127.0.0.1:5080",
        "ZO_ORG": "default",
        "ZO_ACCESS_KEY": "base64_encoded_email:password"
      }
    }
  }
}
```

Replace `/absolute/path/to/openobserve-oss-mcp` with the actual path to this repository.

### Gemini CLI

Add to `~/.gemini/settings.json` (or `.gemini/settings.json` in your project):

**HTTP Transport:**

```json
{
  "mcpServers": {
    "openobserve": {
      "httpUrl": "http://127.0.0.1:8001/mcp",
      "headers": { "Authorization": "Bearer your-auth-token" }
    }
  }
}
```

**Stdio Transport:**

```json
{
  "mcpServers": {
    "openobserve": {
      "command": "uv",
      "args": [
        "run",
        "mcp-server-openobserve",
        "--transport",
        "stdio"
      ],
      "env": {
        "ZO_BASE_URL": "http://127.0.0.1:5080",
        "ZO_ORG": "default",
        "ZO_ACCESS_KEY": "base64_encoded_email:password"
      }
    }
  }
}
```



### Claude Code (CLI)

Stdio:

```bash
claude mcp add openobserve -- \
  uv run mcp-server-openobserve --transport stdio
```

HTTP with a bearer token:

```bash
claude mcp add-json openobserve-http \
  '{"type":"http","url":"http://127.0.0.1:8001/mcp","headers":{"Authorization":"Bearer dev-token"}}'
```

### Codex CLI

Add as HTTP MCP server (for development with `--auth-disabled`):

```bash
codex mcp add openobserve --url http://127.0.0.1:8001/mcp
codex mcp list
```

Or configure directly in `~/.codex/config.toml`:

```toml
[mcp_servers.openobserve]
url = "http://127.0.0.1:8001/mcp"
```

## Troubleshooting

### Connection Issues

**Problem:** Server can't connect to OpenObserve
- Verify `ZO_BASE_URL` is correct and OpenObserve is running
- Test connection: `curl $ZO_BASE_URL/healthz`

**Problem:** Authentication failures
- Ensure `ZO_ACCESS_KEY` is properly base64-encoded
- Test credentials: `curl -u "email:password" $ZO_BASE_URL/api/default/streams`

### Query Issues

**Problem:** SQL queries return no results
- Verify the stream/table exists using `list_streams` tool
- Check time range - use `start_time` and `end_time` parameters
- Ensure your query syntax is valid OpenObserve SQL

**Problem:** Response truncated
- Adjust `--max-rows` or `--max-chars` when starting the server
- Make your SQL query more specific with WHERE clauses and LIMIT

### Client Configuration Issues

**Problem:** MCP server not appearing in Claude Desktop
- Restart Claude Desktop after config changes
- Check logs: `~/Library/Logs/Claude/mcp*.log` (macOS)
- Verify absolute paths in configuration

**Problem:** HTTP transport authentication errors
- Ensure `OPENOBSERVE_MCP_AUTH_TOKEN` matches in server and client
- For development, use `--auth-disabled` flag

## Development

### Running Tests

```bash
uv run pytest
```

### Linting

```bash
uv run ruff check .
uv run ruff format .
```

### Example Scripts

See the `scripts/` directory for example usage:
- `list_streams.py` - List available data streams
- `search_logs.py` - Query logs with SQL
- `ingest_sample_data.py` - Generate test data
- `mcp_client_openobserve.py` - Test MCP server functionality

See [scripts/README.md](scripts/README.md) for detailed usage.

## Security Considerations

- **Read-only:** This server only provides read access to OpenObserve data
- **Local use recommended:** Designed for local OpenObserve instances
- **HTTP auth:** Always use authentication tokens for HTTP transport in production
- **Credential storage:** Never commit `.env` files or hardcode credentials
- **API endpoint restrictions:** `get_api` tool only allows safe, read-only endpoints

## License

MIT

## Contributing

Contributions welcome! Please open an issue or PR on GitHub.

## Links

- [OpenObserve Documentation](https://openobserve.ai/docs/)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [FastMCP Framework](https://github.com/anthropics/fastmcp)
