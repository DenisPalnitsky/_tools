#!/bin/bash

# Stop and remove existing container if it exists
docker stop local-ai-gatewayproxy 2>/dev/null || true
docker rm local-ai-gatewayproxy 2>/dev/null || true

# Build and run the container with port mapping
docker build -t local-proxy . && docker run --name local-ai-gatewayproxy -d -p 9999:9999 local-proxy