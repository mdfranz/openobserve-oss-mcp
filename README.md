# OpenObserve MCP Server

An MCP (Model Context Protocol) server that enables AI assistants to query and explore your OpenObserve observability data. This server provides read-only access to logs, metrics, and traces stored in OpenObserve, allowing LLMs to help you analyze and troubleshoot your systems.

```
user> list the hosts sending journald events
user: list the hosts sending journald events
tool call: list_streams
tool return: list_streams
tool call: get_stream_schema
tool return: get_stream_schema
tool call: search_sql
tool return: search_sql
assistant: I found 2 hosts sending journald events (stream: journald):

- franz-OptiPlex-7050 — 1,960 events — last_seen _timestamp = 1771082221716601 (μs since epoch)
- asus-pn50 — 1,268 events — last_seen _timestamp = 1771082221680679 (μs since epoch)

Query used:
SELECT host_name, COUNT(*) AS cnt, MAX(_timestamp) AS last_seen FROM journald GROUP BY host_name ORDER BY cnt DESC LIMIT 200;

Would you like me to:
- convert the last_seen timestamps to human-readable datetimes, or
- list more hosts, or
- show recent journald messages per host?
```



## Features

- **Read-only access** - Safe querying without data modification
- **Multiple query methods**
  - SQL queries for complex analytics
  - Full-text search for simple log searches
  - Schema discovery to explore data structure
- **Log analytics**
  - Query logs with SQL or full-text search
  - Get log volume histograms over time
  - Discover field schemas for any stream
- **Stream management** - List and explore available data streams
- **Flexible deployment** - Supports both stdio and HTTP transports
- **Multiple clients** - Works with Claude Desktop, Gemini CLI, Codex, and more
- **Configurable limits** - Control response sizes with `--max-rows` and `--max-chars`

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

## Quick Start

1. **Start OpenObserve** (if not already running):
   ```bash
   # See OpenObserve documentation for installation
   docker run -p 5080:5080 public.ecr.aws/zinclabs/openobserve:latest
   ```

2. **Set environment variables**:
   ```bash
   export ZO_BASE_URL=http://127.0.0.1:5080
   export ZO_ORG=default
   export ZO_ACCESS_KEY=$(echo -n "root@example.com:Complexpass#123" | base64)
   ```

3. **Test the MCP server**:
   ```bash
   # List streams
   uv run mcp-server-openobserve --transport stdio
   ```

4. **Configure your AI client** (see [Client Configuration](#client-configuration) section below)

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
- `--max-rows` - Maximum number of rows returned from SQL queries (default: 1000)
- `--max-chars` - Maximum characters in response payload (default: 50000)

## Configuration

### Environment Variables

All configuration can be provided via environment variables or command-line arguments:

**OpenObserve Connection:**
- `ZO_BASE_URL` - OpenObserve instance URL (default: `http://127.0.0.1:5080`)
- `ZO_ORG` - Organization name (default: `default`)
- `ZO_ACCESS_KEY` - Base64-encoded credentials
- `ZO_ROOT_USER_EMAIL` - Email for authentication (alternative to access key)
- `ZO_ROOT_USER_PASSWORD` - Password for authentication (alternative to access key)
- `ZO_TIMEOUT` - Request timeout in seconds (default: 30)

**MCP Server:**
- `MCP_TRANSPORT` - Transport mode: `stdio` or `http` (default: `stdio`)
- `MCP_HOST` - HTTP server host (default: `127.0.0.1`)
- `MCP_PORT` - HTTP server port (default: `8001`)
- `MCP_MAX_ROWS` - Maximum rows per query (default: 1000)
- `MCP_MAX_CHARS` - Maximum response size in characters (default: 50000)
- `MCP_LOG_LEVEL` - Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` (default: `INFO`)
- `OPENOBSERVE_MCP_AUTH_TOKEN` - HTTP transport authentication token (required for HTTP unless `--auth-disabled`)

**Example .env file:**
```bash
# See .env.example for a complete template
ZO_BASE_URL=http://127.0.0.1:5080
ZO_ORG=default
ZO_ACCESS_KEY=base64_encoded_credentials
MCP_LOG_LEVEL=INFO
```

## Available Tools

The MCP server exposes these tools to AI assistants:

### `search_sql`
Run SQL queries against your OpenObserve data.

**Parameters:**
- `sql` (string, required) - SQL query to execute
- `hours` (int, optional) - Query last N hours of data
- `start_micros` (int, optional) - Start timestamp in microseconds
- `end_micros` (int, optional) - End timestamp in microseconds
- `size` (int, optional) - Maximum number of results to return (default: 100)
- `offset` (int, optional) - Number of results to skip (default: 0)

**Example usage:**
```sql
SELECT * FROM nginx_logs WHERE status >= 400 LIMIT 10
```

### `search_logs`
Search logs using full-text search queries (simpler alternative to SQL).

**Parameters:**
- `query` (string, required) - Full-text search query
- `stream` (string, optional) - Stream name to search (default: "default")
- `hours` (int, optional) - Query last N hours (default: 1)
- `size` (int, optional) - Maximum results (default: 100)
- `offset` (int, optional) - Pagination offset (default: 0)

**Example usage:**
```
error AND status:500
```

**Note:** Uses OpenObserve's `match_all()` function for full-text search across all fields.

### `get_log_volume`
Get log volume metrics over time as a histogram.

**Parameters:**
- `stream` (string, optional) - Stream name (default: "default")
- `hours` (int, optional) - Time range in hours (default: 24)
- `interval` (string, optional) - Histogram bucket interval (default: "1 hour")

**Example intervals:** "5 minutes", "1 hour", "1 day"

**Returns:** Time-series histogram showing log counts per time bucket.

### `get_stream_schema`
Get the schema (field names and types) for a specific stream.

**Parameters:**
- `stream` (string, required) - Stream name

**Returns:** Schema information including field names, data types, and metadata.

**Use case:** Discover available fields before writing SQL queries.

### `list_streams`
List all available streams (tables) in your OpenObserve organization.

**Returns:** Array of stream objects with names, types, storage stats, and metadata.

### `get_api`
Make GET requests to specific OpenObserve API endpoints (limited subset for safety).

**Parameters:**
- `path` (string, required) - API endpoint path (without base URL)
- `param` (list of strings, optional) - Query parameters as "key=value" pairs

**Allowed endpoints:**
- `healthz` - Health check endpoint
- `api/{org}/streams` - List streams
- `api/{org}/streams/{stream}/schema` - Get stream schema
- Other organization-scoped read-only endpoints

**Example:**
```python
get_api("api/default/streams")
get_api("api/default/streams/nginx_logs/schema")
```

## Usage Examples

Once configured with an AI assistant, you can use natural language to query your OpenObserve data. Here are some example prompts:

### Exploring Your Data

```
"List all available log streams"
→ Uses list_streams tool

"Show me the schema for the nginx_logs stream"
→ Uses get_stream_schema tool

"What fields are available in my application logs?"
→ Uses get_stream_schema tool
```

### Searching Logs

```
"Find all error logs from the last hour"
→ Uses search_logs with query="error" and hours=1

"Search for 500 errors in nginx logs"
→ Uses search_logs with query="500 AND nginx"

"Show me authentication failures"
→ Uses search_logs with query="authentication AND failed"
```

### SQL Queries

```
"Run SQL: SELECT status, COUNT(*) FROM nginx_logs GROUP BY status"
→ Uses search_sql tool

"Find slow requests: SELECT * FROM app_logs WHERE response_time > 1000 LIMIT 20"
→ Uses search_sql tool

"Show me the top 10 IP addresses by request count"
→ AI constructs appropriate SQL query using search_sql
```

### Analytics and Metrics

```
"Show me log volume for the last 24 hours"
→ Uses get_log_volume with default parameters

"What's the log volume per hour for the last week?"
→ Uses get_log_volume with hours=168 and interval="1 hour"

"Show me error rate trends over the last day"
→ AI combines get_log_volume with filtered queries
```

### Complex Analysis

```
"Compare error rates between production and staging environments"
→ AI uses multiple search_sql queries with WHERE clauses

"Find correlations between high latency and specific error codes"
→ AI constructs complex SQL JOIN or aggregation queries

"Analyze log patterns for service downtime yesterday"
→ AI uses combination of get_log_volume and search_logs
```

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
- `pydantic_ai_agent_mcp_http.py` - Interactive AI agent exploring data via MCP

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
