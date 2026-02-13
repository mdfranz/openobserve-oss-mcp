#!/usr/bin/env python3
from __future__ import annotations

import os
import pprint
import sys

from pydantic_ai import Agent
from pydantic_ai import messages as mcp_messages
from pydantic_ai.mcp import MCPServerStreamableHTTP

SYSTEM_PROMPT = (
    "Explore data sources in OpenObserve using MCP tools based on the query"
)

COLOR_ENABLED = sys.stdout.isatty() and os.getenv("NO_COLOR") is None
COLOR_RESET = "\x1b[0m"
COLOR_BOLD = "\x1b[1m"
COLOR_YELLOW = "\x1b[33m"
COLOR_GREEN = "\x1b[32m"
COLOR_CYAN = "\x1b[36m"
COLOR_MAGENTA = "\x1b[35m"

MAX_CONTENT_CHARS = int(os.getenv("MCP_AGENT_MAX_CHARS", "4000"))


def _color(text: str, color: str) -> str:
    if not COLOR_ENABLED:
        return text
    return f"{COLOR_BOLD}{color}{text}{COLOR_RESET}"


def _format_content(value: object, *, max_chars: int = MAX_CONTENT_CHARS) -> str:
    if isinstance(value, str):
        text = value
    else:
        text = pprint.pformat(value, width=100, compact=False, sort_dicts=True)
    if max_chars > 0 and len(text) > max_chars:
        return f"{text[:max_chars]}... [truncated]"
    return text


def _print_trace(messages: list[mcp_messages.ModelMessage]) -> None:
    for message in messages:
        if isinstance(message, mcp_messages.ModelRequest):
            for part in message.parts:
                if isinstance(part, mcp_messages.SystemPromptPart):
                    continue
                if isinstance(part, mcp_messages.UserPromptPart):
                    content = _format_content(part.content)
                    print(f"{_color('user:', COLOR_CYAN)} {content}")
                elif isinstance(part, mcp_messages.ToolReturnPart):
                    header = f"tool return: {part.tool_name}"
                    print(_color(header, COLOR_MAGENTA))
                elif isinstance(part, mcp_messages.RetryPromptPart):
                    content = _format_content(part.content)
                    print(f"{_color('retry:', COLOR_MAGENTA)} {content}")
        elif isinstance(message, mcp_messages.ModelResponse):
            for part in message.parts:
                if isinstance(part, mcp_messages.TextPart):
                    content = _format_content(part.content)
                    print(f"{_color('assistant:', COLOR_GREEN)} {content}")
                elif isinstance(part, mcp_messages.ToolCallPart):
                    header = f"tool call: {part.tool_name}"
                    print(_color(header, COLOR_YELLOW))
                elif isinstance(part, mcp_messages.BuiltinToolCallPart):
                    header = f"builtin tool call: {part.tool_name}"
                    print(_color(header, COLOR_YELLOW))
                elif isinstance(part, mcp_messages.BuiltinToolReturnPart):
                    header = f"builtin tool return: {part.tool_name}"
                    print(_color(header, COLOR_MAGENTA))

def main() -> None:
    server = MCPServerStreamableHTTP("http://127.0.0.1:8001/mcp")
    agent = Agent("openai:gpt-5-mini", toolsets=[server], system_prompt=SYSTEM_PROMPT)
    print('OpenObserve MCP CLI. Type "/exit" to quit.')
    while True:
        try:
            prompt = input("user> ").strip()
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            break

        if not prompt:
            continue
        if prompt == "/exit":
            break

        result = agent.run_sync(prompt)
        _print_trace(result.all_messages())


if __name__ == "__main__":
    main()
