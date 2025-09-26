import os
from fastapi import FastAPI, Request, Response
import httpx
from colorama import Fore, Back, Style, init

# Initialize colorama for cross-platform colored output
init(autoreset=True)

app = FastAPI()

TARGET_URL =  os.getenv("TARGET_URL", "http://localhost:8080")


print(f"{Fore.GREEN}Proxy Server Starting{Style.RESET_ALL}")
print(f"{Style.DIM}Redirecting traffic to:{Style.RESET_ALL} {Fore.YELLOW}{TARGET_URL}{Style.RESET_ALL}")

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
async def proxy(request: Request, path: str):
    method = request.method    
    url = f"{TARGET_URL}/{path}"
    body = await request.body()
    headers = dict(request.headers)

    # Remove host header to avoid forwarding issues
    headers.pop('host', None)

    print(f"\n{Back.BLUE}{Fore.WHITE} INCOMING REQUEST {Style.RESET_ALL}")
    print(f"{Style.DIM}URL:{Style.RESET_ALL} {Fore.WHITE}{request.url}{Style.RESET_ALL}")
    print(f"{Style.DIM}Method:{Style.RESET_ALL} {Fore.YELLOW}{method}{Style.RESET_ALL}")
    print(f"{Style.DIM}Headers:{Style.RESET_ALL} {Fore.WHITE}{headers}{Style.RESET_ALL}")
    try:
        body_text = body.decode()
        print(f"{Style.DIM}Body:{Style.RESET_ALL} {Fore.WHITE}{body_text}{Style.RESET_ALL}")
    except Exception:
        print(f"{Style.DIM}Body (raw):{Style.RESET_ALL} {Fore.WHITE}{body}{Style.RESET_ALL}")

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

    print(f"\n{Back.GREEN}{Fore.WHITE} OUTGOING RESPONSE {Style.RESET_ALL}")
    
    # Color status code based on HTTP status
    status_color = Fore.GREEN if 200 <= resp.status_code < 300 else Fore.YELLOW if 300 <= resp.status_code < 400 else Fore.RED
    print(f"{Style.DIM}Status:{Style.RESET_ALL} {status_color}{resp.status_code}{Style.RESET_ALL}")
    print(f"{Style.DIM}URL:{Style.RESET_ALL} {Fore.WHITE}{resp.url}{Style.RESET_ALL}")
    print(f"{Style.DIM}Headers:{Style.RESET_ALL} {Fore.WHITE}{dict(resp.headers)}{Style.RESET_ALL}")
    try:
        response_text = resp.text
        print(f"{Style.DIM}Body:{Style.RESET_ALL} {Fore.WHITE}{response_text}{Style.RESET_ALL}")
    except Exception:
        print(f"{Style.DIM}Body (raw):{Style.RESET_ALL} {Fore.WHITE}{resp.content}{Style.RESET_ALL}")

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