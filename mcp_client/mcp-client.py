#!/usr/bin/env python3

import os
import requests

def main():
    base_url = os.getenv("BASE_URL", "http://localhost:9090/mcp")

    # Initialize connection
    init_payload = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {
                "sampling": {},
                "elicitation": {},
                "roots": {
                    "listChanged": True
                }
            },
            "clientInfo": {
                "name": "mcp-inspector",
                "version": "0.16.8"
            }
        }
    }

    # Base headers for initialization
    init_headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }

    print("Initializing MCP connection...")
    response = requests.post(f"{base_url}", json=init_payload, headers=init_headers)
    print(f"Status code: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    print(f"Response text: {response.text}")
    session_id = response.headers.get("mcp-session-id")

    # initialize notifications

    notify_payload = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }

    # Common headers for MCP requests with session
    common_headers = {
        "accept": "application/json, text/event-stream",
        "content-type": "application/json",
        "mcp-protocol-version": "2025-06-18",
        "mcp-session-id": session_id,
        "user-agent": "node-fetch"
    }

    print(f"\nSending notifications/initialized with session_id: {session_id}")
    response = requests.post(f"{base_url}", json=notify_payload, headers=common_headers)
    print(f"Notifications init response: {response.text}")


    # List tools
    tools_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {
            "_meta": {
                "progressToken": 1
            }
        }
    }

    print("\nRequesting list of tools...")
    response = requests.post(f"{base_url}", json=tools_payload, headers=common_headers)
    print(f"Tools response: {response.text}")

if __name__ == "__main__":
    main()