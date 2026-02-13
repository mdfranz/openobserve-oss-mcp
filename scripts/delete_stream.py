#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

# Add src directory to path to import oo_client (src layout)
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from mcp_server_openobserve.oo_client import OpenObserveClient

def main():
    parser = argparse.ArgumentParser(description="Delete a stream")
    parser.add_argument("stream", help="Name of the stream to delete")
    
    args = parser.parse_args()
    
    client = OpenObserveClient()
    
    # Confirm deletion
    confirm = input(f"Are you sure you want to delete stream '{args.stream}'? (y/N): ")
    if confirm.lower() != 'y':
        print("Aborted.")
        return

    try:
        # Construct the API path for deleting a stream
        # Based on OpenObserve API conventions: DELETE /api/{org}/streams/{stream}
        path = f"api/{client.org}/streams/{args.stream}"
        
        response = client._request("DELETE", path)
        print(f"Successfully deleted stream '{args.stream}'. Response: {response.text}")
            
    except Exception as e:
        print(f"Error deleting stream: {e}")

if __name__ == "__main__":
    main()
