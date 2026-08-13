# Закрытый контейнер офиса: SOCKS5-пул (потоковая добыча) + ротатор.
# Выход в интернет — ТОЛЬКО через SOCKS5 из пула. Прямого доступа к сети нет.
FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir pysocks \
    && apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pool/ /app/
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh
