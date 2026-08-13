#!/usr/bin/env python3
"""
rotator.py — SOCKS5-ротатор офиса.

Слушает локальный порт 1080 (socks5) и на КАЖДОЕ новое соединение
выбирает СЛЕДУЮЩИЙ живой прокси из свежего пула (socks5_pool.json).
Пул пересобирается socks_api.py каждые 600 c → всегда свежие прокси.

Поток данных: клиент(агент) -> 127.0.0.1:1080 (ротатор) -> socks5://ip:port из пула -> интернет.
Прямого выхода в интернет из контейнера НЕТ (docker network: только ротатор видит сеть).
"""
import asyncio
import json
import os
import random
import struct
import sys

POOL_FILE = os.environ.get("POOL_FILE", "/output/socks5_pool.json")
LISTEN = os.environ.get("LISTEN_ADDR", "0.0.0.0")
LISTEN_PORT = int(os.environ.get("LISTEN_PORT", "1080"))
MIN_RTT = int(os.environ.get("MIN_RTT", "600"))   # отсекаем прокси медленнее 600 мс
MAX_PROXY_FAILS = int(os.environ.get("MAX_PROXY_FAILS", "3"))

_pool: list = []          # список живых прокси
_cursor: int = 0
_fails: dict = {}         # proxy -> число подряд упавших
_lock = asyncio.Lock()


def load_pool():
    global _pool
    try:
        with open(POOL_FILE) as f:
            data = json.load(f)
        verified = []   # rtt реальный (проверены)
        seeded = []     # rtt 999+ (сид, не проверены)
        for p in data.get("proxies", []):
            if p.get("alive") and p.get("proto") == "socks5":
                rtt = p.get("rtt", 0) or 0
                if rtt and rtt < 900:
                    verified.append(p.get("proxy"))
                else:
                    seeded.append(p.get("proxy"))
        # проверенные вперёд, сид — в конец очереди
        _pool = verified + seeded
        print(f"[rotator] pool reloaded: {len(_pool)} ({len(verified)} verified + {len(seeded)} seed)", flush=True)
    except Exception as e:
        print(f"[rotator] pool load error: {e}", flush=True)


async def pool_loader():
    """Периодически перечитываем пул (свежие прокси от stream_pool)."""
    while True:
        load_pool()
        await asyncio.sleep(int(os.environ.get("POOL_RELOAD", "5")))


def next_proxy():
    global _cursor
    if not _pool:
        return None
    n = len(_pool)
    for _ in range(n):
        _cursor = (_cursor + 1) % n
        proxy = _pool[_cursor]
        if _fails.get(proxy, 0) < MAX_PROXY_FAILS:
            return proxy
    # все прокси помечены плохими — сбрасываем счётчики и берём первый
    _fails.clear()
    return _pool[0]


def mark_fail(proxy):
    _fails[proxy] = _fails.get(proxy, 0) + 1


def mark_ok(proxy):
    _fails.pop(proxy, None)


# ─── SOCKS5 server ──────────────────────────────────────────────

PROXY_TIMEOUT = float(os.environ.get("PROXY_TIMEOUT", "8"))  # таймаут на один прокси


async def try_via_proxy(reader, writer, proxy, host, port, atyp):
    """Пробуем один SOCKS5-прокси: CONNECT к host:port, туннель при успехе.
    Возвращает True, если соединение через прокси установлено."""
    ph, pp = proxy.rsplit(":", 1)
    try:
        pp = int(pp)
    except ValueError:
        mark_fail(proxy)
        return False
    up_r = up_w = None
    try:
        up_r, up_w = await asyncio.wait_for(
            asyncio.open_connection(ph, pp), timeout=PROXY_TIMEOUT)
        up_w.write(b"\x05\x01\x00")
        await asyncio.wait_for(up_w.drain(), timeout=PROXY_TIMEOUT)
        await asyncio.wait_for(up_r.readexactly(2), timeout=PROXY_TIMEOUT)
        if atyp == 1:
            ipbytes = bytes(int(x) for x in host.split("."))
            up_w.write(b"\x05\x01\x00\x01" + ipbytes + struct.pack(">H", port))
        else:
            hb = host.encode()
            up_w.write(b"\x05\x01\x00\x03" + bytes([len(hb)]) + hb + struct.pack(">H", port))
        await asyncio.wait_for(up_w.drain(), timeout=PROXY_TIMEOUT)
        resp = await asyncio.wait_for(up_r.readexactly(4), timeout=PROXY_TIMEOUT)
        if resp[1] != 0:
            mark_fail(proxy)
            return False
        atyp2 = resp[3]
        if atyp2 == 1:
            await asyncio.wait_for(up_r.readexactly(6), timeout=PROXY_TIMEOUT)
        elif atyp2 == 3:
            ln = (await asyncio.wait_for(up_r.readexactly(1), timeout=PROXY_TIMEOUT))[0]
            await asyncio.wait_for(up_r.readexactly(ln + 2), timeout=PROXY_TIMEOUT)
        elif atyp2 == 4:
            await asyncio.wait_for(up_r.readexactly(18), timeout=PROXY_TIMEOUT)

        writer.write(b"\x05\x00\x00\x01\x00\x00\x00\x00\x00\x00")
        await writer.drain()
        mark_ok(proxy)

        async def pump(src, dst):
            try:
                while True:
                    data = await src.read(65536)
                    if not data:
                        break
                    dst.write(data)
                    await dst.drain()
            except Exception:
                pass
            finally:
                try:
                    dst.close()
                except Exception:
                    pass

        await asyncio.gather(pump(reader, up_w), pump(up_r, writer))
        return True
    except Exception:
        mark_fail(proxy)
        try:
            if up_w:
                up_w.close()
            if up_r:
                up_r.close()
        except Exception:
            pass
        return False


async def socks5_handle(reader, writer):
    """Минимальный SOCKS5-сервер (NO AUTH, CONNECT)."""
    peer = writer.get_extra_info("peername")
    try:
        # greeting
        v, nm = await reader.readexactly(2)
        if v != 5:
            return
        await reader.readexactly(nm)
        writer.write(b"\x05\x00")  # no auth
        await writer.drain()
        # request
        ver, cmd, rsv, atyp = await reader.readexactly(4)
        if ver != 5 or cmd != 1:   # только CONNECT
            return
        if atyp == 1:
            host = ".".join(str(b) for b in await reader.readexactly(4))
        elif atyp == 3:
            ln = (await reader.readexactly(1))[0]
            host = (await reader.readexactly(ln)).decode()
        elif atyp == 4:
            host = ".".join(str(b) for b in await reader.readexactly(16))
        else:
            return
        port = struct.unpack(">H", await reader.readexactly(2))[0]

        # failover: пробуем до N прокси на один клиентский запрос
        for attempt in range(int(os.environ.get("FAILOVER", "5"))):
            proxy = next_proxy()
            if not proxy:
                break
            ok = await try_via_proxy(reader, writer, proxy, host, port, atyp)
            if ok:
                return
        # все попытки неудачны
        try:
            writer.write(b"\x05\x05\x00\x01\x00\x00\x00\x00\x00\x00")
            await writer.drain()
        except Exception:
            pass
    except Exception as e:
        print(f"[rotator] conn {peer} err: {type(e).__name__}", flush=True)
    finally:
        try:
            writer.close()
        except Exception:
            pass


async def main():
    load_pool()
    asyncio.create_task(pool_loader())
    server = await asyncio.start_server(socks5_handle, LISTEN, LISTEN_PORT)
    print(f"[rotator] SOCKS5 listening on {LISTEN}:{LISTEN_PORT} ({len(_pool)} proxies in pool)", flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
