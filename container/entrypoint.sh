#!/usr/bin/env bash
# entrypoint.sh — потоковая добыча пула + ротатор, параллельно.
# Прокси добавляются в пул по мере проверки (не ждём валидации всей очереди).
set -e

echo "[entrypoint] starting stream_pool (streaming harvest)"
python /app/stream_pool.py &
POOL_PID=$!

sleep 2

echo "[entrypoint] starting rotator on :1080"
python /app/rotator.py &
ROTATOR_PID=$!

while true; do
  sleep 30
  if ! kill -0 $POOL_PID 2>/dev/null; then
    echo "[entrypoint] stream_pool died, restarting"
    python /app/stream_pool.py &
    POOL_PID=$!
  fi
  if ! kill -0 $ROTATOR_PID 2>/dev/null; then
    echo "[entrypoint] rotator died, restarting"
    python /app/rotator.py &
    ROTATOR_PID=$!
  fi
done
