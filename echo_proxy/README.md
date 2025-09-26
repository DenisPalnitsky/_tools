# Echo Proxy

A simple proxy server that echoes the request and response.

Set target target url (default is https://localhost:8080)
```
export TARGET_URL=https://localhost:8080
```
set port (default is 9090)
```
export PORT=9090
```



## Run locally
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

## Run with Docker
```bash
./run.sh
```



