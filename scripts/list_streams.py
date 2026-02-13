#!/usr/bin/env python3
import json
import sys
from pathlib import Path

# Add src directory to path to import oo_client (src layout)
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from mcp_server_openobserve.oo_client import OpenObserveClient

def main():
    client = OpenObserveClient()
    response = client.get(f"api/{client.org}/streams")
    
    print(f"{'Stream Name':<30} | {'Type':<10} | {'Docs':<10} | {'Size (MB)':<10}")
    print("-" * 70)
    
    for stream in response.get('list', []):
        name = stream.get('name', 'N/A')
        stream_type = stream.get('stream_type', 'N/A')
        stats = stream.get('stats', {})
        doc_num = stats.get('doc_num', 0)
        storage_size = stats.get('storage_size', 0.0)
        size_mb = storage_size / (1024 * 1024)
        
        print(f"{name:<30} | {stream_type:<10} | {doc_num:<10} | {size_mb:<10.2f}")

if __name__ == "__main__":
    main()
