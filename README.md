# OpenObserve MCP Server (Local)

An MCP server for querying a local OpenObserve instance (read/query only).

## Run the server

Stdio:

```bash
uv run mcp-server-openobserve --transport stdio
```

HTTP (requires a token by default):

```bash
export OPENOBSERVE_MCP_AUTH_TOKEN="dev-token"
uv run mcp-server-openobserve --transport http --host 127.0.0.1 --port 8001
```

HTTP without auth (local/dev only):

```bash
uv run mcp-server-openobserve --transport http --host 127.0.0.1 --port 8001 --auth-disabled
```

## Quick start (stdio)

```json
{
  "mcpServers": {
    "openobserve": {
      "command": "uvx",
      "args": ["mcp-server-openobserve", "--transport", "stdio"],
      "env": {
        "ZO_BASE_URL": "http://127.0.0.1:5080",
        "ZO_ORG": "default",
        "ZO_ACCESS_KEY": "<YOUR_BASIC_AUTH_ACCESS_KEY>"
      }
    }
  }
}
```

## Quick start (HTTP)

By default, HTTP transport requires an auth token.

```json
{
  "mcpServers": {
    "openobserve-http": {
      "command": "uvx",
      "args": ["mcp-server-openobserve", "--transport", "http", "--host", "127.0.0.1", "--port", "8001"],
      "env": {
        "ZO_BASE_URL": "http://127.0.0.1:5080",
        "ZO_ORG": "default",
        "ZO_ACCESS_KEY": "<YOUR_BASIC_AUTH_ACCESS_KEY>",
        "OPENOBSERVE_MCP_AUTH_TOKEN": "<YOUR_MCP_HTTP_TOKEN>"
      }
    }
  }
}
```

To run HTTP **without** authentication (local/dev only), add `--auth-disabled`.

## Client setup examples

### Gemini CLI

Add to `~/.gemini/settings.json` (or `.gemini/settings.json` in your project):

Streamable HTTP:

```json
{
  "mcpServers": {
    "openobserve": {
      "httpUrl": "http://127.0.0.1:8001/mcp",
      "headers": { "Authorization": "Bearer dev-token" }
    }
  }
}
```

Stdio:

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
        "ZO_ACCESS_KEY": "<YOUR_BASIC_AUTH_ACCESS_KEY>"
      }
    }
  }
}
```

### Claude Desktop

Edit your `claude_desktop_config.json` (Settings → Developer → Edit Config) and add:

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
        "ZO_ACCESS_KEY": "<YOUR_BASIC_AUTH_ACCESS_KEY>"
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

If you start the server with `--auth-disabled`, you can add it as a streamable HTTP MCP server:

```bash
codex mcp add openobserve --url http://127.0.0.1:8001/mcp
codex mcp list
```

Or configure it directly in `~/.codex/config.toml`:

```toml
[mcp_servers.openobserve]
url = "http://127.0.0.1:8001/mcp"
```

## Tools

- `search_sql`: run an OpenObserve SQL query via `/_search`
- `list_streams`: list streams for the org
- `get_api`: GET a limited set of OpenObserve API endpoints

## Output limits

Use `--max-rows` to cap `search_sql` result size and `--max-chars` to cap response payload size.
