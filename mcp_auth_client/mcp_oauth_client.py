#!/usr/bin/env python3
"""
Simple MCP OAuth Client - connects to MCP server and follows OAuth flow
"""

import requests
import webbrowser
import json
import re
import uuid
import base64
import hashlib
import secrets
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

def start_http_server(port=9999):
        # Start simple HTTP server to receive OAuth callbacks
    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            print("\n📨 Received GET request:")
            print(f"   Path: {self.path}")
            print(f"   Headers: {dict(self.headers)}")

            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>Authorization received!</h1><p>You can close this window.</p></body></html>')

        def do_POST(self):
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else ''

            print("\n📨 Received POST request:")
            print(f"   Path: {self.path}")
            print(f"   Headers: {dict(self.headers)}")
            print(f"   Body: {body}")

            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'<html><body><h1>Request received!</h1><p>Check console for details.</p></body></html>')

        def log_message(self, format, *args):  # noqa: ARG002
            pass  # Suppress default logging

    # Start HTTP server in background thread
    server = HTTPServer(('localhost', 9999), CallbackHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    print("🌐 Started HTTP server on http://localhost:9999")
    print("   Server will print all received requests to console")


def main():
    #mcp_url = "http://localhost:8095"
    mcp_url = "https://mcp-gateway.staging-zende.sk/mcps/zendeskdev"
    #mcp_url ="http://localhost:8095/mcps/zendeskdev"
    session = requests.Session()

    print("MCP OAuth Client")
    print("=" * 20)

    start_http_server()

    # Check if target server is running
    # try:
    #     response = session.get(f"{mcp_url}/health", timeout=5)
    #     print(f"✓ MCP server health: {response.status_code}")
    # except Exception as e:
    #     print(f"✗ Cannot connect to MCP server: {e}")
    #     return

    init_payload = {
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {
                "sampling": {},
                "elicitation": {},
                "roots": {"listChanged": True}
            },
            "clientInfo": {
                "name": "mcp-inspector",
                "version": "0.16.3"
            }
        },
        "jsonrpc": "2.0",
        "id": "1"
    }


    init_resp = session.post(
        f"{mcp_url}?transportType=streamable-http",
        json=init_payload,
        timeout=10,
        headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    )
    print(f"✓ Initialize POST: {init_resp.status_code}")
    if init_resp.status_code != 200:
        print(f"✗ Initialization response: {init_resp.text}")
    print ("www-authenticate:", init_resp.headers['www-authenticate'])

    wwauth = init_resp.headers.get('www-authenticate', '')
    m = re.search(r'resource_metadata="([^"]+)"', wwauth)
    resource_metadata_url = m.group(1) if m else None
    print("resource_metadata:", resource_metadata_url)

    print("Getting resource metadata")
    response = session.get(resource_metadata_url)
    print(f"Status code {response.status_code}")
    if response.status_code != 200:
        print(f"Failed to get resource metadata: {response.text}")
        return

    metadata = response.json()
    print(f"Resource metadata: {json.dumps(metadata, indent=2)}")

    # Extract OAuth information from metadata
    authorization_servers = metadata.get('authorization_servers', [])
    scopes_supported = metadata.get('scopes_supported', [])

    if not authorization_servers:
        print("No authorization servers found in metadata")
        return

    auth_server = authorization_servers[0]
    if not auth_server.endswith('/'):
        auth_server += '/'
    print(f"Using authorization server: {auth_server}")

    # Step 1: Attempt dynamic client registration according to RFC 7591
    print("\n🔧 Attempting dynamic client registration...")

    # Generate PKCE parameters
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')

    # Construct registration endpoint URL
    registration_endpoint = f"{auth_server}register"
    #registration_endpoint = f"{auth_server}/client-registration"

    # Prepare client registration request according to RFC 7591
    client_metadata = {
        "client_name": "MCP OAuth Client",
        "client_uri": "https://github.com/anthropics/claude-code",
        "redirect_uris": [
            "http://localhost:9999/callback",
            "urn:ietf:wg:oauth:2.0:oob"  # Out-of-band for CLI apps
        ],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",  # Public client
        "scope": " ".join(scopes_supported) if scopes_supported else "read",
        "software_id": str(uuid.uuid4()),
        "software_version": "1.0.0"
    }

    # Add MCP-specific metadata
    client_metadata["resource"] = mcp_url

    client_info = None

    print(f"   📝 Registering client at: {registration_endpoint}")
    print(f"   📋 Client metadata: {json.dumps(client_metadata, indent=6)}")

    response = session.post(
        registration_endpoint,
        json=client_metadata,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json,text/event-stream"
        },
        timeout=10
    )

    print(f"   📊 Registration response: {response.status_code}")

    if response.status_code == 201:
        client_data = response.json()
        print("   ✅ Client registered successfully!")
        print(f"   🆔 Client ID: {client_data.get('client_id')}")
        print(f"   🔑 Client Secret: {'***' if client_data.get('client_secret') else 'None (public client)'}")

        client_info = {
            "client_id": client_data.get("client_id"),
            "client_secret": client_data.get("client_secret"),
            "code_verifier": code_verifier,
            "code_challenge": code_challenge,
            "redirect_uris": client_data.get("redirect_uris", client_metadata["redirect_uris"])
        }
    elif response.status_code == 400:
        print(f"   ❌ Bad request: {response.text}")
    elif response.status_code == 403:
        print(f"   ❌ Registration forbidden: {response.text}")
    else:
        print(f"   ❌ Registration failed: {response.status_code} - {response.text}")


    if not client_info:
        print("\n⚠️  Dynamic client registration failed, proceeding with legacy flow...")
        client_info = {"client_id": None, "client_secret": None, "code_verifier": code_verifier, "code_challenge": code_challenge}

    # Step 2: Start OAuth flow using the authorization server from metadata
    print(f"\n2. Starting OAuth flow with scopes: {', '.join(scopes_supported)}")

    # Build authorization URL - typically /oauth/authorize endpoint
    auth_url = f"{auth_server}authorize"

    # Add client_id and PKCE parameters if available
    auth_params = {}
    if client_info.get("client_id"):
        auth_params["client_id"] = client_info["client_id"]
        auth_params["response_type"] = "code"
        auth_params["scope"] = " ".join(scopes_supported) if scopes_supported else "read"
        auth_params["resource"] = mcp_url  # MCP Resource Indicator

        if client_info.get("redirect_uris"):
            auth_params["redirect_uri"] = client_info["redirect_uris"][0]

        if client_info.get("code_challenge"):
            auth_params["code_challenge"] = client_info["code_challenge"]
            auth_params["code_challenge_method"] = "S256"


    # Use proper OAuth parameters if we have client registration
    response = session.get(auth_url, params=auth_params, allow_redirects=False)
    print(f"   Auth start: {response.status_code}")

    if response.status_code in [302, 303, 307, 308]:
        redirect_url = response.headers.get('location')
        print(f"   Redirect URL: {redirect_url}")

        # Open browser for user to authorize
        print("   Opening browser...")
        webbrowser.open(redirect_url)

        # Wait for user to complete authorization
        if client_info and client_info.get("client_id"):
            # For dynamic client registration, we need to handle the authorization code
            print("\n   After authorization, you should receive an authorization code.")
            print("   If redirected to a URL, copy the 'code' parameter from the URL.")
            auth_code = input("   Enter the authorization code (or press Enter to skip): ").strip()

            if auth_code:
                # Exchange authorization code for access token using PKCE
                print("\n🔄 Exchanging authorization code for access token...")
                token_endpoint = f"{auth_server}oauth/token"

                token_data = {
                    "grant_type": "authorization_code",
                    "code": auth_code,
                    "client_id": client_info["client_id"],
                    "resource": mcp_url  # MCP Resource Indicator
                }

                if client_info.get("redirect_uris"):
                    token_data["redirect_uri"] = client_info["redirect_uris"][0]

                if client_info.get("code_verifier"):
                    token_data["code_verifier"] = client_info["code_verifier"]

                if client_info.get("client_secret"):
                    token_data["client_secret"] = client_info["client_secret"]

                try:
                    response = session.post(
                        token_endpoint,
                        data=token_data,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        timeout=10
                    )

                    if response.status_code == 200:
                        token_info = response.json()
                        print("✅ Token exchange successful!")
                        print(f"🎫 Access token: {'***' + token_info.get('access_token', '')[-8:] if token_info.get('access_token') else 'None'}")

                        # Add Bearer token to session headers
                        session.headers.update({
                            "Authorization": f"Bearer {token_info['access_token']}"
                        })
                        print("   ✅ Bearer token added to session headers")
                    else:
                        print(f"❌ Token exchange failed: {response.status_code} - {response.text}")

                except Exception as e:
                    print(f"❌ Token exchange error: {e}")
        else:
            input("\n   Press Enter after completing authorization in browser...")

        # Step 3: Test if we're authenticated by making a request with Bearer token
        print("\n3. Testing authentication...")

        # Try to access the protected resource with session cookies or Bearer token
        response = session.get(f"{mcp_url}/mcp", timeout=10)
        print(f"   MCP endpoint: {response.status_code}")

        if response.status_code == 200:
            print("   ✓ Successfully authenticated!")
            try:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)[:200]}...")
            except Exception:
                print(f"   Response: {response.text[:100]}...")
        elif response.status_code == 401:
            print("   ✗ Still not authenticated - OAuth flow may have failed")
            print(f"   Response: {response.text}")
        else:
            print(f"   Response: {response.status_code} - {response.text[:100]}")

        # Step 4: Test additional endpoints if authenticated
        if response.status_code == 200:
            print("\n4. Testing additional endpoints...")
            test_endpoints = ["/auth/session", "/health"]

            for endpoint in test_endpoints:
                response = session.get(f"{mcp_url}{endpoint}")
                print(f"   {endpoint}: {response.status_code}")

                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"      {json.dumps(data, indent=6)[:200]}...")
                    except Exception:
                        print(f"      {response.text[:100]}...")
                elif response.status_code == 401:
                    print("      ✗ Not authenticated")
                elif response.status_code == 403:
                    print("      ✗ Forbidden")

        print("\n✓ OAuth flow complete!")

    else:
        print(f"   ✗ Unexpected response: {response.status_code}")
        print(f"   Response: {response.text}")
        print(f"   Headers: {dict(response.headers)}")

        # If direct auth failed, try the original endpoints as fallback
        print("\n   Trying fallback endpoints...")

        # Try original auth endpoints
        test_endpoints = [f"{mcp_url}/auth/info", f"{mcp_url}/auth/authorize"]
        for endpoint in test_endpoints:
            response = session.get(endpoint, allow_redirects=False)
            print(f"   {endpoint}: {response.status_code}")
            if response.status_code in [302, 303, 307, 308]:
                redirect_url = response.headers.get('location')
                print(f"      Redirect to: {redirect_url}")
                if redirect_url:
                    print("      Opening browser...")
                    webbrowser.open(redirect_url)
                    input("\n      Press Enter after completing authorization in browser...")
                    break

if __name__ == "__main__":
    main()