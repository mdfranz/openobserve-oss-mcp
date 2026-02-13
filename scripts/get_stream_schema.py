#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

# Add src directory to path to import oo_client (src layout)
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from mcp_server_openobserve.client import OpenObserveClient


def main():
    parser = argparse.ArgumentParser(description="Get schema for a stream")
    parser.add_argument(
        "stream", nargs="?", default="default", help="Stream name (default: default)"
    )

    args = parser.parse_args()

    client = OpenObserveClient()

    try:
        response = client.get_stream_schema(args.stream)
        print(json.dumps(response, indent=2))
    except Exception as e:
        print(f"Error getting schema: {e}")


if __name__ == "__main__":
    main()
