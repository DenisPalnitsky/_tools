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
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode

# Shared state for OAuth callback
oauth_state = {
    "code": None,
    "error": None,
    "event": threading.Event()
}

def start_http_server(port=9999):
    # Start simple HTTP server to receive OAuth callbacks
    class CallbackHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith("/favicon.ico"):
                self.send_response(404)
                self.end_headers()
                return

            print("\n📨 Received GET request:")
            print(f"   Path: {self.path}")
            print(f"   Headers: {dict(self.headers)}")
    

            # Parse query parameters from the callback URL
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            
            print(f"   Query parameters: {params}")
            
            # Extract authorization code or error
            if 'code' in params:
                oauth_state["code"] = params['code'][0]
                print(f"   ✅ Authorization code captured: {oauth_state['code'][:20]}...")
            elif 'error' in params:
                oauth_state["error"] = params['error'][0]
                print(f"   ❌ OAuth error: {oauth_state['error']}")
            
            # Signal that callback was received
            oauth_state["event"].set()

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
    return server


def main():
    #mcp_url = "https://api.githubcopilot.com/mcp"    
    session = requests.Session()

    print("MCP OAuth Client")
    print("=" * 20)

    server = start_http_server()

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
    response = session.get(resource_metadata_url )
    print(f"Status code {response.status_code}")
    if response.status_code != 200:
        print(f"Resource medatata failed with HTTP status code: {response.status_code} and response: {response.text}")
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
    
    # Fetch authorization server metadata (RFC 8414)
    print("\n🔍 Fetching authorization server metadata...")
    as_metadata_url = f"{auth_server}.well-known/oauth-authorization-server"
    try:
        as_response = session.get(as_metadata_url, timeout=10)
        if as_response.status_code == 200:
            as_metadata = as_response.json()
            print(f"   Authorization server metadata: {json.dumps(as_metadata, indent=6)}")
            token_endpoint = as_metadata.get('token_endpoint')
            authorization_endpoint = as_metadata.get('authorization_endpoint')
            registration_endpoint = as_metadata.get('registration_endpoint')
        else:
            print(f"   Could not fetch AS metadata: {as_response.status_code}")
            token_endpoint = None
            authorization_endpoint = None
            registration_endpoint = None
    except Exception as e:
        print(f"   Error fetching AS metadata: {e}")
        token_endpoint = None
        authorization_endpoint = None
        registration_endpoint = None

    # Step 1: Attempt dynamic client registration according to RFC 7591
    print("\n🔧 Attempting dynamic client registration...")

    # Generate PKCE parameters
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').rstrip('=')
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode('utf-8')).digest()
    ).decode('utf-8').rstrip('=')

    # Use registration endpoint from metadata or construct default
    if not registration_endpoint:
        registration_endpoint = f"{auth_server}register"

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
        server.shutdown()
        return
    if not client_info.get("client_id"):
        print("\n⚠️  No client ID found, exiting...")
        server.shutdown()
        return
    if  not client_info.get("redirect_uris"):
        print("\n⚠️  No redirect URIs found, exiting...")
        server.shutdown()
        return
    if not client_info.get("code_challenge"):
        print("\n⚠️  No code challenge found, exiting...")
        server.shutdown()
        return


    # !!!!!!!!!!!!!! OAUTH FLOW !!!!!!!!!!!!!!
    # Step 2: Start OAuth flow using the authorization server from metadata
    print(f"\n2. Starting OAuth flow with scopes: {', '.join(scopes_supported)}")

    # Build authorization URL from metadata or use default
    auth_url = authorization_endpoint if authorization_endpoint else f"{auth_server}authorize"
    print(f"   Authorization URL: {auth_url}")

    # Add client_id and PKCE parameters if available
    auth_params = {}
  
    auth_params["client_id"] = client_info["client_id"]
    auth_params["response_type"] = "code"
    auth_params["scope"] = " ".join(scopes_supported) if scopes_supported else "read"
    auth_params["resource"] = mcp_url  # MCP Resource Indicator
    auth_params["redirect_uri"] = client_info["redirect_uris"][0]   
    auth_params["code_challenge"] = client_info["code_challenge"]
    auth_params["code_challenge_method"] = "S256"
    auth_params["state"] = str(uuid.uuid4())

    # Use proper OAuth parameters if we have client registration
    response = session.get(auth_url, params=auth_params, allow_redirects=False)
    print(f"   Auth start: {response.status_code}")

    if response.status_code in [302, 303, 307, 308]:
        redirect_url = response.headers.get('location')
        print(f"   Redirect URL: {redirect_url}")

        # Open browser for user to authorize
        print("   Opening browser...")
        webbrowser.open(redirect_url)

        # Wait for OAuth callback
        if client_info and client_info.get("client_id"):
            print("\n   ⏳ Waiting for OAuth callback...")
            
            # Wait up to 120 seconds for the callback
            if oauth_state["event"].wait(timeout=120):
                if oauth_state["error"]:
                    print(f"\n❌ OAuth error received: {oauth_state['error']}")
                    server.shutdown()
                    return
                
                auth_code = oauth_state["code"]
                if auth_code:
                    print(f"\n✅ Authorization code received!")
                else:
                    print("\n❌ No authorization code in callback")
                    server.shutdown()
                    return
            else:
                print("\n⏱️ Timeout waiting for OAuth callback")
                server.shutdown()
                return

            if auth_code:
                # Exchange authorization code for access token using PKCE
                print("\n🔄 Exchanging authorization code for access token...")
                token_url = token_endpoint if token_endpoint else f"{auth_server}token"
                print(f"   Token endpoint: {token_url}")

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

                print(f"   Token request data: {token_data}")
                print(f"   Token request data (URL encoded): {urlencode(token_data)}")

                try:
                    response = session.post(
                        token_url,
                        data=token_data,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        timeout=10
                    )

                    print(f"   Token response status: {response.status_code}")
                    print(f"   Token response headers: {dict(response.headers)}")
                    
                    if response.status_code == 200:
                        token_info = response.json()
                        print("✅ Token exchange successful!")
                        print(f"🎫 Access token: {'***' + token_info.get('access_token', '')[-8:] if token_info.get('access_token') else 'None'}")
                        print(f"   Full token response: {json.dumps(token_info, indent=6)}")

                        # Add Bearer token to session headers
                        session.headers.update({
                            "Authorization": f"Bearer {token_info['access_token']}"
                        })
                        print("   ✅ Bearer token added to session headers")
                    else:
                        print(f"❌ Token exchange failed: {response.status_code}")
                        print(f"   Response body: {response.text}")
                        print(f"   Response headers: {dict(response.headers)}")

                except Exception as e:
                    print(f"❌ Token exchange error: {e}")
        else:
            print("\n   ℹ️ No client_id available, skipping automatic token exchange")
        
        # Check what cookies we have after OAuth flow
        print("\n📋 Current session state:")
        print(f"   Cookies: {dict(session.cookies)}")
        print(f"   Headers: {dict(session.headers)}")

        # Step 3: Test if we're authenticated by making a request with Bearer token
        print("\n3. Testing authentication with MCP initialize request...")

        # Generate a session ID for MCP
        mcp_session_id = str(uuid.uuid4())
        
        # Create proper MCP initialize request
        test_payload = {
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


        response = session.post(f"{mcp_url}?transportType=streamable-http", json=test_payload, headers={"Content-Type": "application/json", "Accept": "application/json, text/event-stream", "Authorization": f"Bearer {token_info['access_token']}"})
        print(f"   Response: {response.status_code} - {response.text}")
        
        print("🛑 Shutting down server...")
        server.shutdown()

if __name__ == "__main__":
    main()