# Exploration Scripts for OpenObservability

These scripts demonstrate how to use `src/mcp_server_openobserve/oo_client.py` to interact with your OpenObservability instance.

## Prerequisites

Ensure you have your environment variables set:

```bash
export ZO_ROOT_USER_EMAIL=mdfranz@gmail.com
export ZO_ROOT_USER_PASSWORD='Complexpa$$789'
export ZO_BASE_URL=http://127.0.0.1:5080
```

And activate your virtual environment:

```bash
source ../.venv/bin/activate
pip install -r ../requirements.txt
```

## Available Scripts

### 0. MCP Client Smoke Test

Uses Pydantic AI's MCP client to call tools on `mcp-server-openobserve` over either HTTP or stdio.

```bash
pip install -r ../requirements.txt
```

HTTP (server already running):

```bash
export OPENOBSERVE_MCP_AUTH_TOKEN="dev-token"   # unless server started with --auth-disabled
python3 mcp_client_openobserve.py http --url http://127.0.0.1:8001/mcp
```

Run a search query (SQL must reference a stream/table):

```bash
python3 mcp_client_openobserve.py http --url http://127.0.0.1:8001/mcp \
  --sql "select * from nginx limit 5" --hours 24
```

stdio (spawns server via `uv` from this repo):

```bash
export ZO_BASE_URL=http://127.0.0.1:5080
export ZO_ORG=default
export ZO_ACCESS_KEY="..."
python3 mcp_client_openobserve.py stdio
```

### 1. List Streams

Lists all available streams and their basic stats (document count, size).

```bash
python3 list_streams.py
```

### 2. Ingest Sample Data

Ingests sample log records into a stream.

```bash
# Ingest 10 records into 'sample_logs' (default)
python3 ingest_sample_data.py

# Ingest 50 records into 'my_stream'
python3 ingest_sample_data.py --stream my_stream --count 50
```

### 3. Search Logs

Search logs in a stream using SQL or simple parameters.

```bash
# Search 'sample_logs' (default)
python3 search_logs.py

# Search specific stream with limit
python3 search_logs.py --stream my_stream --limit 20

# Use custom SQL query
python3 search_logs.py --sql "SELECT * FROM my_stream WHERE level='ERROR' LIMIT 5"
```

### 4. Delete Stream

Delete a stream (be careful!).

```bash
python3 delete_stream.py my_stream
```
