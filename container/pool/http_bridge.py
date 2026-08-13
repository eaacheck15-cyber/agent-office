#!/usr/bin/env python3
"""
http_bridge.py — HTTP/HTTPS CONNECT-прокси → SOCKS5-ротатор.
Даёт HTTP-прокси (127.0.0.1:8081) поверх SOCKS5-ротатора (127.0.0.1:1080).
Нужен для инструментов, поддерживающих ТОЛЬКО HTTP-прокси (nikto и т.п.):
каждый CONNECT-запрос уходит через ротатор → перебор живых SOCKS5-прокси из пула.
"""
import asyncio
import os
import struct

HTTP_LISTEN = os.environ.get("HTTP_LISTEN", "127.0.0.1")
HTTP_PORT = int(os.environ.get("HTTP_PORT", "8081"))
SOCKS_HOST = os.environ.get("SOCKS_HOST", "127.0.0.1")
SOCKS_PORT = int(os.environ.get("SOCKS_PORT", "1080"))


async def socks_connect(dst_host: bytes, dst_port: int, atyp: int):
    """CONNECT к цели через SOCKS5-ротатор. Возвращает (reader, writer)."""
    r, w = await asyncio.open_connection(SOCKS_HOST, SOCKS_PORT)
    w.write(b"\x05\x01\x00")          # версия 5, 1 метод, no auth
    await w.drain()
    await r.readexactly(2)
    if atyp == 1:
        w.write(b"\x05\x01\x00\x01" + dst_host + struct.pack(">H", dst_port))
    else:
        w.write(b"\x05\x01\x00\x03" + bytes([len(dst_host)]) + dst_host + struct.pack(">H", dst_port))
    await w.drain()
    resp = await r.readexactly(4)
    if resp[1] != 0:
        w.close()
        raise ConnectionError(f"socks connect failed: {resp[1]}")
    atyp2 = resp[3]
    if atyp2 == 1:
        await r.readexactly(6)
    elif atyp2 == 3:
        ln = (await r.readexactly(1))[0]
        await r.readexactly(ln + 2)
    elif atyp2 == 4:
        await r.readexactly(18)
    return r, w


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


async def handle(reader, writer):
    try:
        # читаем первую строку запроса (CONNECT host:port HTTP/1.1)
        line = await reader.readline()
        parts = line.decode("latin1", "replace").strip().split(" ")
        if len(parts) < 2 or parts[0].upper() != "CONNECT":
            # не CONNECT — закрываем (этот мост только для HTTPS-туннелей)
            writer.write(b"HTTP/1.1 405 Method Not Allowed\r\nContent-Length: 0\r\n\r\n")
            await writer.drain()
            writer.close()
            return
        host, port = parts[1].rsplit(":", 1)
        port = int(port)
        # сброс остальных заголовков
        while True:
            h = await reader.readline()
            if h in (b"\r\n", b"\n", b""):
                break
        # резолвим: если IP — atyp=1, если имя — atyp=3
        try:
            import ipaddress
            ip = ipaddress.ip_address(host)
            atyp = 1 if ip.version == 4 else 4
            dst_host = ip.packed
        except ValueError:
            atyp = 3
            dst_host = host.encode()
        up_r, up_w = await socks_connect(dst_host, port, atyp)
        writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        await writer.drain()
        await asyncio.gather(pump(reader, up_w), pump(up_r, writer))
    except Exception as e:
        try:
            writer.write(b"HTTP/1.1 502 Bad Gateway\r\nContent-Length: 0\r\n\r\n")
            await writer.drain()
        except Exception:
            pass
        try:
            writer.close()
        except Exception:
            pass


async def main():
    server = await asyncio.start_server(handle, HTTP_LISTEN, HTTP_PORT)
    print(f"[http-bridge] HTTP CONNECT proxy on {HTTP_LISTEN}:{HTTP_PORT} -> SOCKS {SOCKS_HOST}:{SOCKS_PORT}", flush=True)
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
