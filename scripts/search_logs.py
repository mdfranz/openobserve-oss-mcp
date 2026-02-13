#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

# Add src directory to path to import oo_client (src layout)
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from mcp_server_openobserve.oo_client import OpenObserveClient

def main():
    parser = argparse.ArgumentParser(description="Search logs in a stream")
    parser.add_argument("--stream", default="sample_logs", help="Stream name (default: sample_logs)")
    parser.add_argument("--limit", type=int, default=10, help="Number of records to return (default: 10)")
    parser.add_argument("--sql", help="Full SQL query (overrides stream and limit)")
    
    args = parser.parse_args()
    
    client = OpenObserveClient()
    
    if args.sql:
        sql = args.sql
    else:
        sql = f"SELECT * FROM {args.stream} LIMIT {args.limit}"
    
    print(f"Executing SQL: {sql}")
    
    try:
        response = client.search(sql=sql)
        hits = response.get('hits', [])
        print(f"Found {len(hits)} records.")
        
        for hit in hits:
            print(json.dumps(hit, indent=2))
            
    except Exception as e:
        print(f"Error searching data: {e}")

if __name__ == "__main__":
    main()
