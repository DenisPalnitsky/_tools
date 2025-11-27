# MCP OAuth Client

A command-line tool for testing OAuth 2.0 authentication flow with MCP (Model Context Protocol) servers.

## Description

This tool demonstrates a complete OAuth 2.0 flow with PKCE and dynamic client registration (RFC 7591). It:
- Connects to an MCP server
- Performs dynamic client registration
- Starts a local HTTP server to receive OAuth callbacks
- Opens a browser for user authorization
- Exchanges authorization code for access token
- Tests authenticated requests to the MCP server

## Usage

Set path to mcp by setting `mcp_url` variable in `mcp_oauth_client.py` file.

```bash
# Install dependencies
uv sync

# Run the client
uv run python mcp_oauth_client.py
```

The tool will:
1. Start a local HTTP server on `http://localhost:9999`
2. Open your browser for authorization
3. Print the OAuth flow details and token information to the console

