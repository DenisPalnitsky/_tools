import os
import json
import warnings
from datetime import datetime
from urllib.parse import urljoin
from fastapi import FastAPI, Request, Response
import httpx
from colorama import Fore, Back, Style, init

# Suppress the pkg_resources deprecation warning from old protobuf versions
warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf")

from formatter import format_body

# Initialize colorama for cross-platform colored output
init(autoreset=True)

app = FastAPI()

TARGET_URL =  os.getenv("TARGET_URL", "http://localhost:8080")
ECHO_MODE = os.getenv("ECHO_MODE", "false").lower() in ("true", "1", "yes")

# Track last request time for smart spacing
last_request_time = None


print(f"{Fore.GREEN}Proxy Server Starting{Style.RESET_ALL}")
if ECHO_MODE:
    print(f"{Fore.MAGENTA}Echo Mode: Enabled (all requests will return 200 without forwarding){Style.RESET_ALL}")
else:
    print(f"{Style.DIM}Redirecting traffic to:{Style.RESET_ALL} {Fore.YELLOW}{TARGET_URL}{Style.RESET_ALL}")

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy(request: Request, path: str):
    global last_request_time
    
    # Smart spacing: add separator if more than a minute has passed
    current_time = datetime.now()
    if last_request_time is not None:
        time_diff = (current_time - last_request_time).total_seconds()
        if time_diff > 60:  # More than a minute
            print("\n\n\n----------------------------------------------------------------------\n\n\n")
    last_request_time = current_time
    
    method = request.method    
    # Properly construct the target URL with query parameters
    query_string = str(request.url.query) if request.url.query else ""
    target_path = path if path else ""
    url = urljoin(TARGET_URL + "/", target_path)
    if query_string:
        url = f"{url}?{query_string}"
    body = await request.body()
    headers = dict(request.headers)

    # Remove host header to avoid forwarding issues
    headers.pop('host', None)

    timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"\n\n\n{Back.BLUE}{Fore.WHITE} INCOMING REQUEST {Style.RESET_ALL} {Fore.CYAN}{timestamp}{Style.RESET_ALL}")
    print(f"{Style.DIM}URL:{Style.RESET_ALL} {Fore.WHITE}{request.url}{Style.RESET_ALL}")
    print(f"{Style.DIM}Target URL:{Style.RESET_ALL} {Fore.CYAN}{url}{Style.RESET_ALL}")
    print(f"{Style.DIM}Method:{Style.RESET_ALL} {Fore.YELLOW}{method}{Style.RESET_ALL}")
    print(f"{Style.DIM}Headers:{Style.RESET_ALL} {Fore.WHITE}{headers}{Style.RESET_ALL}")
    
    content_type = headers.get("content-type", "")
    formatted_body = format_body(body, content_type)
    print(f"{Style.DIM}Body:{Style.RESET_ALL} {Fore.WHITE}{formatted_body}{Style.RESET_ALL}")

    # If echo mode is enabled, return 200 without forwarding
    if ECHO_MODE:
        echo_response = {
            "echo": True,
            "method": method,
            "path": path,
            "headers": headers,
            "body": formatted_body
        }
        response_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"\n{Back.MAGENTA}{Fore.WHITE} ECHO RESPONSE {Style.RESET_ALL} {Fore.CYAN}{response_timestamp}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}Status: 200 OK{Style.RESET_ALL}")
        print(f"{Style.DIM}Echoing request without forwarding{Style.RESET_ALL}")
        
        return Response(
            content=json.dumps(echo_response, indent=2),
            status_code=200,
            headers={"content-type": "application/json"}
        )

    # Configure client with no timeouts and increased limits
    timeout = httpx.Timeout(None)  # No timeout
    limits = httpx.Limits(max_keepalive_connections=100, max_connections=1000)
    
    try:
        async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
            resp = await client.request(
                method,
                url,
                content=body,
                headers=headers,
                follow_redirects=True,
            )
    except httpx.ConnectError as e:
        error_msg = f"Failed to connect to target: {url}. Error: {str(e)}"
        print(f"\n{Back.RED}{Fore.WHITE} CONNECTION ERROR {Style.RESET_ALL}")
        print(f"{Fore.RED}{error_msg}{Style.RESET_ALL}")
        print(f"{Style.DIM}TARGET_URL env variable:{Style.RESET_ALL} {Fore.YELLOW}{TARGET_URL}{Style.RESET_ALL}")
        print(f"{Style.DIM}Make sure the target server is running and accessible{Style.RESET_ALL}")
        return Response(
            content=json.dumps({"error": error_msg}, indent=2),
            status_code=502,
            headers={"content-type": "application/json"}
        )

    response_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"\n{Back.GREEN}{Fore.WHITE} OUTGOING RESPONSE {Style.RESET_ALL} {Fore.CYAN}{response_timestamp}{Style.RESET_ALL}")
    
    # Color status code based on HTTP status
    status_color = Fore.GREEN if 200 <= resp.status_code < 300 else Fore.YELLOW if 300 <= resp.status_code < 400 else Fore.RED
    print(f"{Style.DIM}Status:{Style.RESET_ALL} {status_color}{resp.status_code}{Style.RESET_ALL}")
    print(f"{Style.DIM}URL:{Style.RESET_ALL} {Fore.WHITE}{resp.url}{Style.RESET_ALL}")
    print(f"{Style.DIM}Headers:{Style.RESET_ALL} {Fore.WHITE}{dict(resp.headers)}{Style.RESET_ALL}")
    
    response_content_type = resp.headers.get("content-type", "")
    formatted_response = format_body(resp.content, response_content_type)
    print(f"{Style.DIM}Body:{Style.RESET_ALL} {Fore.WHITE}{formatted_response}{Style.RESET_ALL}")

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=dict(resp.headers)
    )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 9090))
    host = os.getenv("HOST", "0.0.0.0") 
    
    print(f"{Fore.CYAN}Starting server on {host}:{port}{Style.RESET_ALL}")
    uvicorn.run(app, host=host, port=port)