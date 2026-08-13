#!/usr/bin/env bash
# run.sh — сборка и запуск закрытого контейнера с SOCKS5-пулом.
set -e
cd "$(dirname "$0")"

mkdir -p pool/output

if command -v docker >/dev/null 2>&1; then
  docker build -t agent-office-proxy .
  docker rm -f agent-office-proxy 2>/dev/null || true
  docker run -d \
    --name agent-office-proxy \
    --restart unless-stopped \
    -p 127.0.0.1:1080:1080 \
    -p 127.0.0.1:8912:8904 \
    -v "$(pwd)/pool/output:/output" \
    -e SOCKS_REFRESH_EVERY=600 \
    -e POOL_RELOAD=60 \
    -e MIN_RTT=600 \
    -e MAX_PROXY_FAILS=3 \
    -e LISTEN_PORT=1080 \
    --cap-drop ALL \
    --security-opt no-new-privileges:true \
    --tmpfs /tmp \
    agent-office-proxy \
    bash /app/entrypoint.sh
  echo "Container started. SOCKS5: 127.0.0.1:1080  |  pool API: http://127.0.0.1:8912/status"
else
  echo "docker not found. Используйте docker-compose: docker compose up -d --build"
  exit 1
fi
