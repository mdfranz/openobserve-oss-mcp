# OpenObserve MCP Server

An MCP (Model Context Protocol) server that enables AI assistants to query and explore your OpenObserve observability data. This server provides read-only access to logs, metrics, and traces stored in OpenObserve, allowing LLMs to help you analyze and troubleshoot your systems.

```
(mcp-server-openobserve) mfranz@lenovo-cr14p:~/github/openobserve-oss-mcp$ uv run scripts/o2_mcp_client.py --model google:gemini-3-pro-preview
Info: 'google:' provider is ambiguous. Assuming 'google-gla:' (Google Generative Language API).
Initializing agent with model: google-gla:gemini-3-pro-preview
OpenObserve MCP CLI. Type "/exit" to quit.
user> what streams are there?
user: what streams are there?
tool call: list_streams
tool return: list_streams
assistant: The available streams are:
- **suricata** (Type: logs, Doc count: ~13.5 million)

```



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
