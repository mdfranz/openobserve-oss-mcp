#!/usr/bin/env python3
from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPServerStreamableHTTP


def main() -> None:
    server = MCPServerStreamableHTTP("http://127.0.0.1:8001/mcp")
    agent = Agent("openai:gpt-5-mini", toolsets=[server])

    prompt = (
        "Explore all available data sources in OpenObserve using MCP tools. "
        "First list all streams. Then summarize the data sources and explain "
        "what each appears to represent (logs vs metrics, likely origin) in plain language. "
        "Be concise and group similar system_* metrics together."
    )
    result = agent.run_sync(prompt)
    print(result.output)


if __name__ == "__main__":
    main()
