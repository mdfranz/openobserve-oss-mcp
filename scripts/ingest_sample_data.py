#!/usr/bin/env python3
import argparse
import random
import sys
import time
from pathlib import Path

# Add src directory to path to import oo_client (src layout)
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from mcp_server_openobserve.oo_client import OpenObserveClient

def main():
    parser = argparse.ArgumentParser(description="Ingest sample logs into a stream")
    parser.add_argument("--stream", default="sample_logs", help="Stream name (default: sample_logs)")
    parser.add_argument("--count", type=int, default=10, help="Number of records to ingest (default: 10)")
    
    args = parser.parse_args()
    
    client = OpenObserveClient()
    records = []
    
    levels = ["INFO", "WARN", "ERROR", "DEBUG"]
    services = ["auth", "payment", "frontend", "backend"]
    
    print(f"Generating {args.count} sample records for stream '{args.stream}'...")
    
    for i in range(args.count):
        record = {
            "timestamp": int(time.time() * 1000000), # microseconds
            "level": random.choice(levels),
            "service": random.choice(services),
            "message": f"Sample log message {i+1}",
            "latency": random.randint(10, 500)
        }
        records.append(record)
        
    try:
        response = client.ingest_json(args.stream, records)
        print("Ingestion response:", response)
        print(f"Successfully ingested {len(records)} records into '{args.stream}'.")
    except Exception as e:
        print(f"Error ingesting data: {e}")

if __name__ == "__main__":
    main()
