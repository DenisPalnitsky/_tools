# Agent Documentation - Developer Tools Collection

## Project Overview

This repository contains a collection of developer tools designed for debugging, testing, and development workflows. The project consists of three main components:

1. **Echo Proxy** - A debugging proxy server that logs and forwards HTTP requests
2. **MCP Client** - A Model Context Protocol (MCP) client for testing MCP servers
3. **MCP OAuth Client** - An advanced MCP client with OAuth authentication support

## Project Structure

```
/Users/denis.palnitsky/Code/github.com/DenisPalnitsky/_tools/
├── echo_proxy/           # HTTP proxy server for debugging
│   ├── main.py          # FastAPI proxy server implementation
│   ├── requirements.txt # Python dependencies
│   ├── Dockerfile       # Container configuration
│   ├── docker-compose.yml # Docker Compose setup
│   ├── run-docker.sh    # Docker execution script
│   ├── run-local.sh     # Local execution script
│   └── README.md        # Echo proxy documentation
├── mcp_client/          # Basic MCP protocol client
│   ├── mcp-client.py    # HTTP-based MCP client
│   └── README.md        # MCP client documentation
├── mcp_auth_client/     # Advanced MCP client with OAuth
│   ├── mcp_oauth_client.py # OAuth-enabled MCP client
│   └── README_mcp_client.md # OAuth client documentation
├── LICENSE              # Project license
├── README.md           # Main project documentation
├── AGENT.md            # Agent documentation (this file)
└── .gitignore          # Git ignore patterns
```

## Component Details

### Echo Proxy (`echo_proxy/`)

**Purpose**: A transparent HTTP proxy that logs all incoming requests and outgoing responses with colored terminal output for debugging purposes.

**Key Features**:
- Forwards HTTP requests to configurable target URL
- Logs request/response details with color-coded output
- Supports all HTTP methods (GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD)
- Handles binary and text content
- No timeout limits for long-running requests
- Docker and local execution support

**Configuration**:
- `TARGET_URL`: Target server URL (default: `http://localhost:8080`)
- `PORT`: Proxy server port (default: `9090`)
- `HOST`: Bind address (default: `0.0.0.0`)

**Dependencies**:
- FastAPI (>=0.104.0) - Web framework
- uvicorn (>=0.24.0) - ASGI server
- httpx (>=0.25.0) - HTTP client
- requests (>=2.31.0) - HTTP library
- colorama (>=0.4.6) - Terminal colors

**Usage**:
```bash
# Local execution
cd echo_proxy/
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py

# Docker execution
./run-docker.sh
```

### MCP Client (`mcp_client/`)

**Purpose**: A simple HTTP-based client for testing Model Context Protocol (MCP) servers without WebSocket dependencies.

**Key Features**:
- Implements MCP initialization handshake
- Session management with session IDs
- Tool listing functionality
- Pure HTTP implementation (no WebSocket required)

**Configuration**:
- `BASE_URL`: MCP server base URL (default: `http://localhost:9090/mcp`)

**Usage**:
```bash
cd mcp_client/
python mcp-client.py
```

### MCP OAuth Client (`mcp_auth_client/`)

**Purpose**: An advanced MCP client that implements OAuth 2.0 authentication flow with PKCE (Proof Key for Code Exchange) for secure authentication with MCP servers.

**Key Features**:
- OAuth 2.0 authorization code flow with PKCE
- Dynamic client registration (RFC 7591)
- Built-in HTTP callback server for OAuth redirects
- Automatic browser integration for user authorization
- Bearer token management and session handling
- Comprehensive request/response logging
- MCP resource metadata discovery
- Support for multiple OAuth scopes

**Configuration**:
- MCP server URL (configurable in code, default: `http://localhost:3000/mcps/zendeskdev`)
- OAuth callback server port (default: `9999`)
- Automatic redirect URI: `http://localhost:9999/callback`

**Dependencies**:
- requests - HTTP client library
- Standard library modules: webbrowser, json, re, uuid, base64, hashlib, secrets, threading, http.server

**OAuth Flow**:
1. **Resource Discovery**: Fetches OAuth metadata from MCP server
2. **Client Registration**: Attempts dynamic client registration with OAuth provider
3. **Authorization**: Opens browser for user to authorize the application
4. **Token Exchange**: Exchanges authorization code for access token using PKCE
5. **Authentication Testing**: Validates authentication with protected MCP endpoints

**Usage**:
```bash
cd mcp_auth_client/
python mcp_oauth_client.py
```

**Security Features**:
- PKCE (Proof Key for Code Exchange) for public clients
- Secure random code generation
- SHA256 code challenge method
- Bearer token protection
- Session-based authentication

## Development Guidelines

### Code Style
- Python 3.8+ compatible
- Type hints recommended but not enforced
- FastAPI async/await patterns for web services
- Environment variable configuration
- Comprehensive error handling and logging

### Testing Approach
- Manual testing through proxy requests
- MCP protocol compliance testing
- Docker container testing
- Cross-platform compatibility (macOS, Linux, Windows)

### Common Tasks

**Adding New Tools**:
1. Create new directory under project root
2. Include `README.md` with usage instructions
3. Add entry to main `README.md`
4. Follow existing patterns for configuration and execution

**Modifying Echo Proxy**:
- Main logic in `main.py`
- Request/response handling in the `proxy()` function
- Color output using colorama library
- Configuration via environment variables

**Extending MCP Client**:
- Core protocol logic in `mcp-client.py`
- Add new MCP methods as separate functions
- Maintain session state across requests
- Handle JSON-RPC 2.0 protocol compliance

**Extending MCP OAuth Client**:
- OAuth flow implementation in `mcp_oauth_client.py`
- Modify OAuth endpoints and scopes as needed
- Add new authentication methods
- Extend callback server functionality
- Handle different OAuth providers

### Environment Setup

**Prerequisites**:
- Python 3.8+
- Docker (optional, for containerized execution)
- Virtual environment recommended

**Installation**:
```bash
# Clone and setup
git clone <repository-url>
cd _tools

# Setup echo proxy
cd echo_proxy/
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Setup basic MCP client (uses standard library only)
cd ../mcp_client/
# No additional dependencies required

# Setup OAuth MCP client
cd ../mcp_auth_client/
pip install requests  # Only additional dependency needed
```

### Debugging and Troubleshooting

**Echo Proxy Issues**:
- Check target URL accessibility
- Verify port availability
- Review proxy logs for request/response details
- Test with simple HTTP clients (curl, Postman)

**MCP Client Issues**:
- Verify MCP server is running and accessible
- Check JSON-RPC request/response format
- Validate session ID handling
- Review MCP protocol version compatibility

**MCP OAuth Client Issues**:
- Ensure OAuth provider is properly configured
- Check redirect URI matches registered OAuth application
- Verify OAuth scopes are supported by the provider
- Review browser console for authorization errors
- Check callback server accessibility on localhost:9999
- Validate PKCE implementation with OAuth provider
- Review OAuth metadata endpoint responses

### Security Considerations

- Echo proxy forwards all headers and content (avoid sensitive data in logs)
- Basic MCP client has no authentication or authorization implemented
- OAuth MCP client implements secure PKCE flow for public clients
- OAuth tokens and secrets are handled securely in memory
- Callback server runs on localhost only (not exposed externally)
- Intended for development/testing environments only
- Docker containers run with default security settings
- OAuth client supports secure authorization code flow with state validation

### Performance Notes

- Echo proxy configured for high connection limits
- No request timeouts (suitable for long-running operations)
- Minimal request/response processing overhead
- Colored logging may impact performance in high-traffic scenarios

## Integration Points

**With Other Tools**:
- Echo proxy can intercept traffic from any HTTP client
- Basic MCP client can test any MCP-compliant server
- OAuth MCP client can authenticate with OAuth-protected MCP servers
- All tools designed for development workflow integration
- OAuth client can work with various OAuth 2.0 providers (Zendesk, etc.)

**CI/CD Considerations**:
- Docker images can be built for deployment
- Environment variables allow configuration flexibility
- No persistent state or database dependencies
