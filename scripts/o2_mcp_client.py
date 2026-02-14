#!/usr/bin/env python3
from __future__ import annotations

import os
import pprint
import sys
import readline
import atexit
import argparse

from pydantic_ai import Agent
from pydantic_ai import messages as mcp_messages
from pydantic_ai.mcp import MCPServerStreamableHTTP

SYSTEM_PROMPT = """
You are an expert OpenObserve Assistant. Your goal is to help users query and analyze their logs and observability data.

Follow these Standard Operating Procedures:
1. **Discovery (CRITICAL)**: You do NOT know the available streams. You MUST call `list_streams` first to see what streams are available. NEVER guess a stream name (like 'container_cpu_usage' or 'logs').
2. **Schema Awareness**: Before writing complex SQL with `search_sql`, ALWAYS call `get_stream_schema` for the target stream to ensure you use correct field names and types.
3. **Search Strategy**:
   - For simple text searches (e.g. "find errors"), use `search_logs`.
   - For aggregations, specific field filtering, or time-based analysis, use `search_sql`.
4. **SQL Syntax**: OpenObserve uses a SQL dialect similar to PostgreSQL/MySQL.

When investigating issues, look for 'error' or 'exception' in the logs unless directed otherwise.
"""

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


import logging

# Configure logging. Default to WARNING to reduce noise.
# Can be set to INFO or DEBUG via MCP_AGENT_LOG_LEVEL environment variable.
log_level = os.getenv("MCP_AGENT_LOG_LEVEL", "WARNING").upper()
logging.basicConfig(level=getattr(logging, log_level, logging.WARNING))
logger = logging.getLogger(__name__)

def main() -> None:
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="OpenObserve MCP Agent CLI")
    parser.add_argument(
        "--model", 
        type=str, 
        default="openai:gpt-5.2", 
        help="Model identifier (e.g., 'openai:gpt-5.2', 'google:gemini-3-flash-preview', 'anthropic:claude-haiku-4-5')"
    )
    args = parser.parse_args()

    # Setup readline history
    history_file = os.path.expanduser("~/.openobserve_mcp_history")
    try:
        readline.read_history_file(history_file)
    except FileNotFoundError:
        pass
    
    # Save history on exit
    atexit.register(readline.write_history_file, history_file)

    server = MCPServerStreamableHTTP("http://127.0.0.1:8001/mcp", max_retries=5)
    
    model_name = args.model
    if model_name.startswith("google:"):
        print(f"{_color('Info:', COLOR_YELLOW)} 'google:' provider is ambiguous. Assuming 'google-gla:' (Google Generative Language API).")
        model_name = model_name.replace("google:", "google-gla:", 1)

    print(f"Initializing agent with model: {_color(model_name, COLOR_CYAN)}")
    agent = Agent(model_name, toolsets=[server], system_prompt=SYSTEM_PROMPT, retries=5)
    
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

        try:
            result = agent.run_sync(prompt)
            _print_trace(result.all_messages())
        except Exception as e:
            print(f"{_color('Error:', COLOR_MAGENTA)} {e}")
            import traceback
            traceback.print_exc()
            print(f"\n{_color('Tip:', COLOR_YELLOW)} If you see 'UnexpectedModelBehavior' or tool errors, check your MCP server logs.")
            print("Ensure the MCP server is running with valid credentials in .env")

if __name__ == "__main__":
    main()
