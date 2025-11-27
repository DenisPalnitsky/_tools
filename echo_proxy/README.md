# Echo Proxy

A simple proxy server that echoes the request and response.

## Configuration

Set target target url (default is https://localhost:8080)
```
export TARGET_URL=https://localhost:8080
```
Set port (default is 9090)
```
export PORT=9090
```
Enable echo mode to return 200 without forwarding (default is false)
```
export ECHO_MODE=true
```

When `ECHO_MODE` is enabled, the proxy will respond to all requests with a 200 status code and a JSON body containing the request details, without forwarding the request to the target URL. This is useful for testing and debugging.

## Features

- **Automatic body formatting**: The proxy automatically formats request and response bodies based on content-type:
  - JSON: Pretty-printed with indentation
  - XML: Pretty-printed with indentation
  - Protobuf: Decoded to JSON format (requires `blackboxprotobuf`)
  - Binary data: Base64 encoded
  - Plain text: Displayed as-is
- **Colored terminal output**: Easy-to-read color-coded request/response logs
- **Timestamps**: Each request and response is timestamped with millisecond precision
- **Echo mode**: Test mode that returns 200 OK without forwarding requests



## Run locally
```bash
# Install uv if you haven't already
# curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies and run
uv run main.py
```

Or use the provided script:
```bash
./run-local.sh
```

## Run with Docker
```bash
./run.sh
```






