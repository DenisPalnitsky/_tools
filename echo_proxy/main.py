import os
import json
import warnings
from datetime import datetime
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


print(f"{Fore.GREEN}Proxy Server Starting{Style.RESET_ALL}")
if ECHO_MODE:
    print(f"{Fore.MAGENTA}Echo Mode: Enabled (all requests will return 200 without forwarding){Style.RESET_ALL}")
else:
    print(f"{Style.DIM}Redirecting traffic to:{Style.RESET_ALL} {Fore.YELLOW}{TARGET_URL}{Style.RESET_ALL}")

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy(request: Request, path: str):
    method = request.method    
    url = f"{TARGET_URL}/{path}"
    body = await request.body()
    headers = dict(request.headers)

    # Remove host header to avoid forwarding issues
    headers.pop('host', None)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"\n{Back.BLUE}{Fore.WHITE} INCOMING REQUEST {Style.RESET_ALL} {Fore.CYAN}{timestamp}{Style.RESET_ALL}")
    print(f"{Style.DIM}URL:{Style.RESET_ALL} {Fore.WHITE}{request.url}{Style.RESET_ALL}")
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
    
    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        resp = await client.request(
            method,
            url,
            content=body,
            headers=headers,
            follow_redirects=True,
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