#!/usr/bin/env python3
from __future__ import annotations

import argparse
import atexit
import json
import os
import readline
import sys
import time
from pathlib import Path
from typing import Any

# Add src directory to path to import oo_client (src layout)
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from mcp_server_openobserve.oo_client import OpenObserveClient

COLOR_ENABLED = sys.stdout.isatty() and os.getenv("NO_COLOR") is None
COLOR_RESET = "\x1b[0m"
COLOR_BOLD = "\x1b[1m"
COLOR_YELLOW = "\x1b[33m"
COLOR_GREEN = "\x1b[32m"
COLOR_CYAN = "\x1b[36m"
COLOR_MAGENTA = "\x1b[35m"

def _color(text: str, color: str) -> str:
    if not COLOR_ENABLED:
        return text
    return f"{COLOR_BOLD}{color}{text}{COLOR_RESET}"

def print_table(data: list[dict[str, Any]]) -> None:
    if not data:
        print("No results.")
        return

    # Get all keys from all records to ensure we don't miss any columns
    # but for large sets we might want to just use the first few or limit it
    keys = []
    for row in data:
        for k in row.keys():
            if k not in keys:
                keys.append(k)
    
    # Calculate column widths
    widths = {k: len(str(k)) for k in keys}
    for row in data:
        for k in keys:
            val = str(row.get(k, ""))
            if len(val) > widths[k]:
                widths[k] = min(len(val), 50)  # Max width 50

    # Print header
    header = " | ".join(f"{k:<{widths[k]}}" for k in keys)
    print(_color(header, COLOR_CYAN))
    print("-" * len(header))

    # Print rows
    for row in data:
        line = " | ".join(f"{str(row.get(k, ''))[:widths[k]]:<{widths[k]}}" for k in keys)
        print(line)

def main() -> None:
    parser = argparse.ArgumentParser(description="OpenObserve SQL Shell")
    parser.add_argument("--hours", type=int, default=24, help="Lookback window in hours (default: 24)")
    parser.add_argument("--size", type=int, default=100, help="Maximum results to return (default: 100)")
    args = parser.parse_args()

    try:
        client = OpenObserveClient()
    except ValueError as e:
        print(f"{_color('Error:', COLOR_MAGENTA)} {e}")
        print("Please set ZO_BASE_URL, ZO_ORG, and ZO_ACCESS_KEY (or ZO_ROOT_USER_EMAIL/PASSWORD).")
        sys.exit(1)

    # Setup readline history
    history_file = os.path.expanduser("~/.openobserve_sql_history")
    try:
        readline.read_history_file(history_file)
    except FileNotFoundError:
        pass
    
    atexit.register(readline.write_history_file, history_file)

    print(f"Connected to {_color(client.base_url, COLOR_CYAN)} (Org: {_color(client.org, COLOR_CYAN)})")
    print(f"Time window: last {_color(str(args.hours) + ' hours', COLOR_YELLOW)}. (Use --hours to change)")
    print('Type SQL queries (end with ;). Type "/exit", "/quit", or Ctrl-D to exit.')
    print('Type "/streams" to list available streams.')
    
    buffer = []
    while True:
        try:
            prompt = "sql> " if not buffer else ".. > "
            line = input(prompt).strip()
        except EOFError:
            print()
            break
        except KeyboardInterrupt:
            print()
            if buffer:
                buffer = []
                print("Query cleared.")
                continue
            break

        if not line and not buffer:
            continue
        
        if not buffer:
            if line.lower() in ("/exit", "/quit", "exit", "quit"):
                break

            if line == "/streams":
                try:
                    res = client.get(f"api/{client.org}/streams")
                    streams = []
                    for s in res.get('list', []):
                        streams.append({
                            "name": s.get('name'),
                            "type": s.get('stream_type'),
                            "docs": s.get('stats', {}).get('doc_num'),
                            "size_mb": round(s.get('stats', {}).get('storage_size', 0) / (1024*1024), 2)
                        })
                    print_table(streams)
                except Exception as e:
                    print(f"{_color('Error listing streams:', COLOR_MAGENTA)} {e}")
                continue

            if line.startswith("/schema "):
                parts = line.split(None, 1)
                if len(parts) < 2:
                    print("Usage: /schema <stream_name>")
                    continue
                stream = parts[1]
                try:
                    res = client.get(f"api/{client.org}/{stream}/schema")
                    print(json.dumps(res, indent=2))
                except Exception as e:
                    print(f"{_color(f'Error getting schema for {stream}:', COLOR_MAGENTA)} {e}")
                continue

        buffer.append(line)
        if not line.endswith(";"):
            continue
            
        sql_query = " ".join(buffer).strip().rstrip(";")
        buffer = []

        # Execute SQL
        try:
            now = int(time.time() * 1_000_000)
            start_micros = now - args.hours * 60 * 60 * 1_000_000
            end_micros = now + 60 * 60 * 1_000_000
            
            start_exec = time.time()
            result = client.search(
                sql=sql_query,
                start_time_micros=start_micros,
                end_time_micros=end_micros,
                size=args.size
            )
            elapsed = time.time() - start_exec
            
            hits = result.get('hits', [])
            print_table(hits)
            
            total = result.get('total', len(hits))
            took = result.get('took', int(elapsed * 1000))
            print(f"\n{_color(f'{len(hits)} hits', COLOR_YELLOW)} (Total: {total}) in {_color(f'{took}ms', COLOR_YELLOW)}")
            
        except Exception as e:
            print(f"{_color('SQL Error:', COLOR_MAGENTA)} {e}")

if __name__ == "__main__":
    main()
