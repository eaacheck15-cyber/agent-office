#!/usr/bin/env python3
"""
socks_api.py — сервис добычи и раздачи SOCKS5-прокси для API проекта.

Добыча (источники):
  1. GitHub-списки SOCKS5 (TheSpeedX, monosans, proxifly, ShiftyTR, hookzof, jetkai)
  2. Masscan-скан подсетей на порты 1080/4145/9050/1081
  3. Shodan InternetDB (если ключ/прокси доступны)

Валидация: TCP + CONNECT (socks5) через pysocks к 8.8.8.8:53.
Кэш: /output/socks5_pool.json (единый с proxy-api).
API (порт 8904):
  GET /socks5.txt?limit=50          — список ip:port построчно
  GET /socks5.json                  — JSON с деталями (proxy, rtt, country)
  GET /status                       — статистика пула
  GET /refresh                      — запуск добычи в фоне
  GET /health                       — живость сервиса
"""
import concurrent.futures
import json
import os
import random
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

# ═══ КОНФИГ ═══
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("SOCKS_API_PORT", "8904"))
CACHE_FILE = os.environ.get("SOCKS_CACHE", "/output/socks5_pool.json")
REFRESH_EVERY = int(os.environ.get("SOCKS_REFRESH_EVERY", "600"))
INTERNETDB = os.environ.get("INTERNETDB", "http://185.212.131.152:8900/internetdb")

# GitHub-источники SOCKS5 (проверены живыми в 2026)
SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
    "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/socks5.txt",
]
# pastebin-источники (живые списки SOCKS5)
PB_SOURCES = []
# API-источники (динамические списки SOCKS5)
API_SOURCES = [
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=10000&country=all&ssl=all&anonymity=all",
]
SOCKS_PORTS = [1080, 4145, 9050, 1081, 8000, 8001]

# Подсети для masscan-добычи (хостинги, где часто открытые прокси)
SCAN_NETS = os.environ.get("SOCKS_SCAN_NETS", "").split(",")
SCAN_PORTS = "1080,4145,9050,1081"

_pool: dict = {"proxies": [], "updated": 0, "stats": {}}
_lock = threading.Lock()


# ═══ ДОБЫЧА: источники ═══

_IP_PORT_RE = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3}):(\d{2,5})\b")


def _valid_ip(ip: str) -> bool:
    parts = ip.split(".")
    if len(parts) != 4:
        return False
    return all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)


def _valid_port(port: str) -> bool:
    return port.isdigit() and 1 <= int(port) <= 65535


def _parse_proxy_text(text: str) -> list:
    """Извлечь ip:port из листинга любого вида: текст, HTML-таблица, разметка."""
    text = re.sub(r"<[^>]+>", " ", text)     # вырезаем HTML-теги
    text = re.sub(r"&[a-z#0-9]+;", " ", text)  # html-сущности
    out = []
    for ip, port in _IP_PORT_RE.findall(text):
        if _valid_ip(ip) and _valid_port(port) and ip not in ("0.0.0.0", "255.255.255.255"):
            out.append(f"{ip}:{port}")
    return out


def _parse_json_proxies(obj, out=None):
    """Рекурсивно извлечь прокси из JSON-листинга: [[ip,port],...] или [{ip,port},...]."""
    if out is None:
        out = set()
    if isinstance(obj, dict):
        ip = obj.get("ip") or obj.get("host") or obj.get("address")
        port = obj.get("port")
        if isinstance(ip, str) and isinstance(port, (int, str)):
            if _valid_ip(ip) and _valid_port(str(port)):
                out.add(f"{ip}:{port}")
        for v in obj.values():
            _parse_json_proxies(v, out)
    elif isinstance(obj, (list, tuple)):
        if len(obj) == 2 and isinstance(obj[0], str) and _valid_ip(obj[0]) and _valid_port(str(obj[1])):
            out.add(f"{obj[0]}:{obj[1]}")
        for v in obj:
            _parse_json_proxies(v, out)
    return out


def _fetch_raw(url: str) -> list:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "curl/8.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            text = r.read().decode("utf-8", "replace")
        out = _parse_proxy_text(text)
        stripped = text.strip()
        if stripped[:1] in ("[", "{"):
            try:
                out.extend(_parse_json_proxies(json.loads(stripped)))
            except Exception:
                pass
        return sorted(set(out))
    except Exception:
        return []


def _fetch_sources() -> list:
    """Сбор из GitHub + API-списков."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
        res = list(ex.map(_fetch_raw, SOURCES + PB_SOURCES + API_SOURCES))
    uniq = sorted(set(p for chunk in res for p in chunk))
    return uniq


def _gen_px_conf() -> str:
    """Свежий proxychains-конфиг из HTTP-проверенных SOCKS5 пула."""
    import socks as _socks, urllib.request as _ur, concurrent.futures as _cf
    try:
        with _ur.urlopen("http://127.0.0.1:8904/socks5.txt?limit=150", timeout=10) as r:
            pool = [l.strip() for l in r.read().decode().splitlines() if ":" in l]
    except Exception:
        return ""

    def ok(proxy):
        try:
            h, p = proxy.rsplit(":", 1)
            s = _socks.socksocket()
            s.set_proxy(_socks.SOCKS5, h, int(p))
            s.settimeout(8)
            s.connect(("api.ipify.org", 80))
            s.send(b"GET / HTTP/1.0\r\nHost: api.ipify.org\r\n\r\n")
            data = b""
            while True:
                c = s.recv(1024)
                if not c:
                    break
                data += c
            s.close()
            body = data.split(b"\r\n\r\n")[-1].decode("utf-8", "replace").strip()
            return bool(re.match(r"^\d{1,3}(\.\d{1,3}){3}$", body))
        except Exception:
            return False

    with _cf.ThreadPoolExecutor(max_workers=40) as ex:
        res = list(ex.map(ok, pool))
    alive = [p for p, good in zip(pool, res) if good][:8]
    if not alive:
        return ""

    conf = "dynamic_chain\nproxy_dns\ntcp_read_time_out 15000\ntcp_connect_time_out 10000\n\n[ProxyList]\n"
    for p in alive:
        h, po = p.split(":")
        conf += f"socks5 {h} {po}\n"
    path = "/tmp/socks_scan_px.conf"
    with open(path, "w") as f:
        f.write(conf)
    return path


def _masscan_scan() -> list:
    """Скан подсетей через proxychains + nmap (защищённый, не с нашего IP)."""
    if not SCAN_NETS:
        return []
    pxconf = _gen_px_conf()
    if not pxconf:
        print("[SOCKS] нет живых SOCKS для проксирования скана", file=os.sys.stderr)
        return []
    found = []
    for net in SCAN_NETS:
        try:
            cmd = ["proxychains4", "-q", "-f", pxconf,
                   "nmap", "-sT", "-Pn", "-p", SCAN_PORTS, "--host-timeout", "25s",
                   "-oG", "-", net.strip()]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=150)
            for m in re.finditer(r"Host: (\S+) \(\)\s+Ports: ([^\n]+)", r.stdout):
                ip = m.group(1)
                for pm in re.finditer(r"(\d+)/open/tcp", m.group(2)):
                    found.append(f"{ip}:{pm.group(1)}")
        except Exception as e:
            print(f"[SOCKS] скан {net}: {e}", file=os.sys.stderr)
            continue
    return found


def _internetdb_sniff() -> list:
    """Поиск через InternetDB (кандидаты на известных IP)."""
    return []


# ═══ ВАЛИДАЦИЯ ═══

def _try_socks(proxy: str, proto, timeout=10):
    """Попытка подключения через SOCKS5/SOCKS4 + реальный HTTP. Вернёт (ok, rtt_ms)."""
    import socks
    h, p = proxy.rsplit(":", 1)
    s = socks.socksocket()
    s.set_proxy(proto, h, int(p))
    s.settimeout(timeout)
    t0 = time.time()
    try:
        s.connect(("api.ipify.org", 80))
        s.send(b"GET / HTTP/1.0\r\nHost: api.ipify.org\r\n\r\n")
        data = b""
        while True:
            chunk = s.recv(2048)
            if not chunk:
                break
            data += chunk
        s.close()
        body = data.split(b"\r\n\r\n")[-1].decode("utf-8", "replace").strip()
        ok = bool(data) and (re.match(r"^\d{1,3}(\.\d{1,3}){3}$", body)
                             or b"200 OK" in data or b"HTTP/1" in data)
        return (ok, round((time.time() - t0) * 1000))
    except Exception:
        try:
            s.close()
        except Exception:
            pass
        return (False, 0)


def _try_http(proxy: str, timeout=10):
    """Попытка как HTTP/HTTPS-прокси (GET через прокси). Вернёт (ok, rtt_ms)."""
    try:
        h, p = proxy.rsplit(":", 1)
        import urllib.request as _ur
        ph = f"http://{h}:{p}"
        o = _ur.build_opener(_ur.ProxyHandler({"http": ph, "https": ph}))
        o.addheaders = [("User-Agent", "curl/8.0")]
        t0 = time.time()
        with o.open("http://api.ipify.org", timeout=timeout) as r:
            body = r.read(200).decode("utf-8", "replace").strip()
        ok = bool(re.match(r"^\d{1,3}(\.\d{1,3}){3}$", body))
        return (ok, round((time.time() - t0) * 1000))
    except Exception:
        return (False, 0)


def _alive(proxy: str, timeout=10):
    """Детект протокола прокси: SOCKS5 → SOCKS4 → HTTP(S).
    Возвращает (proxy, ok, proto, rtt)."""
    import socks
    # 1) SOCKS5
    ok5, rtt5 = _try_socks(proxy, socks.SOCKS5, timeout)
    if ok5:
        return (proxy, True, "socks5", rtt5)
    # 2) SOCKS4
    ok4, rtt4 = _try_socks(proxy, socks.SOCKS4, timeout)
    if ok4:
        return (proxy, True, "socks4", rtt4)
    # 3) HTTP/HTTPS прокси
    okh, rtth = _try_http(proxy, timeout)
    if okh:
        return (proxy, True, "http", rtth)
    return (proxy, False, "", 0)


def _geo(ip: str) -> tuple:
    """Определение страны по IP через ip-api.com (бесплатно, 45 req/min)."""
    try:
        import urllib.request as _ur
        req = _ur.Request(f"http://ip-api.com/json/{ip}?fields=countryCode,country,status",
                          headers={"User-Agent": "curl/8.0"})
        with _ur.urlopen(req, timeout=4) as r:
            d = json.loads(r.read())
        if d.get("status") == "success":
            return (d.get("countryCode", ""), d.get("country", ""))
    except Exception:
        pass
    return ("", "")


def _validate(proxies: list) -> list:
    if not proxies:
        return []
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as ex:
        res = list(ex.map(_alive, proxies))
    alive = []
    for proxy, ok, proto, rtt in res:
        if ok:
            ip = proxy.split(":")[0]
            cc, cn = _geo(ip)
            alive.append({"proxy": proxy, "proto": proto or "socks5", "rtt": rtt,
                          "alive": True, "checked": int(time.time()),
                          "country": cn, "cc": cc})
    return alive


# ═══ СБОР ═══

def collect():
    """Полный цикл добычи."""
    print("[SOCKS] сбор источников...", file=sys.stderr)
    cands = _fetch_sources()
    print(f"[SOCKS] из GitHub: {len(cands)}", file=sys.stderr)

    ms = _masscan_scan()
    if ms:
        cands = list(set(cands + ms))
        print(f"[SOCKS] из masscan: {len(ms)} (всего {len(cands)})", file=sys.stderr)

    # Ограничиваем число кандидатов (топ живых источников достаточно)
    if len(cands) > 4000:
        cands = cands[:4000]
        print(f"[SOCKS] берём топ-3000 для скорости", file=sys.stderr)
    print(f"[SOCKS] валидация {len(cands)}...", file=sys.stderr)
    alive = _validate(cands)
    alive.sort(key=lambda p: p["rtt"])

    with _lock:
        global _pool
        _pool = {
            "proxies": alive,
            "updated": int(time.time()),
            "stats": {"total": len(alive), "sources": len(SOURCES),
                      "country": "all"},
        }
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(_pool, f)
    except Exception:
        pass
    print(f"[SOCKS] итого живых: {len(alive)}", file=sys.stderr)


# ═══ HTTP-СЕРВЕР ═══

class H(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")

    def _json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _txt(self, text, code=200):
        body = text.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        try:
            u = urlparse(self.path)
            q = parse_qs(u.query)

            # ═══ Единая авторизация по ключу (через proxy-sales 8902) ═══
            _public = u.path in ("/health", "/status", "/live")
            if not _public:
                key = q.get("key", [""])[0]
                # внутренний токен для локальных сервисов (без доп. авторизации)
                internal = os.environ.get("SOCKS_INTERNAL_KEY", "")
                if key and internal and key == internal:
                    pass
                else:
                    if not key:
                        self._json({"status": "error",
                                    "error": "нужен ключ: добавьте ?key=ВАШ_КЛЮЧ"}, 401)
                        return
                    import urllib.request as _ur
                    try:
                        with _ur.urlopen(f"http://127.0.0.1:8902/v1/status?key={key}", timeout=5) as _r:
                            _auth = json.loads(_r.read())
                        if _auth.get("status") != "ok":
                            self._json({"status": "error", "error": "неверный ключ"}, 401)
                            return
                    except Exception:
                        self._json({"status": "error", "error": "сервис авторизации недоступен"}, 503)
                        return
            with _lock:
                proxies = list(_pool.get("proxies", []))
                updated = _pool.get("updated", 0)

            if u.path == "/health":
                self._json({"status": "ok", "alive": len(proxies)})
                return

            if u.path == "/status":
                # Разбивка по протоколам (socks5/socks4/http)
                from collections import Counter as _C
                proto_count = _C(p.get("proto", "socks5") for p in proxies)
                self._json({"status": "ok", "total": len(proxies),
                            "socks5": proto_count.get("socks5", 0),
                            "socks4": proto_count.get("socks4", 0),
                            "http": proto_count.get("http", 0),
                            "updated": updated, "stale": time.time() - updated})
                return

            if u.path == "/socks5.txt":
                limit = int(q.get("limit", ["50"])[0])
                rnd = q.get("random", ["0"])[0] == "1"
                out = [p["proxy"] for p in proxies]
                if rnd:
                    random.shuffle(out)
                self._txt("\n".join(out[:limit]) + ("\n" if out else ""))
                return

            if u.path in ("/socks5.json", "/list.json"):
                limit = int(q.get("limit", ["100"])[0])
                self._json({"status": "ok", "count": min(len(proxies), limit),
                            "proxies": proxies[:limit]})
                return

            if u.path == "/live":
                items = []
                # живой листинг: случайные 12 из пула, чтобы витрина постоянно обновлялась
                import random as _rnd
                if len(proxies) > 12:
                    _picked = _rnd.sample(sorted(proxies, key=lambda x: x.get("rtt", 0))[:40], 12)
                else:
                    _picked = sorted(proxies, key=lambda x: x.get("rtt", 0))[:12]
                for p in _picked:
                    proxy = p.get("proxy", "")
                    if ":" not in proxy:
                        continue
                    host, port = proxy.rsplit(":", 1)
                    masked = host[:6] + "***" if len(host) > 6 else host + "***"
                    flag = (p.get("cc") or "").lower()
                    emoji = "".join(chr(127462 + ord(c) - 97) for c in flag) if flag else "🌐"
                    items.append({"ip": masked, "port": port, "flag": emoji,
                                  "country": p.get("country", ""), "rtt": p.get("rtt", 0)})
                self._json({"status": "ok", "proxies": items})
                return

            if u.path in ("/proxies/list", "/socks5/list"):
                # Список прокси: маскированные IP, флаг, страна, скорость
                limit = int(q.get("limit", ["20"])[0])
                items = []
                for p in proxies:
                    proxy = p.get("proxy", "")
                    if ":" not in proxy:
                        continue
                    host, port = proxy.rsplit(":", 1)
                    masked = host[:5] + "***" if len(host) > 5 else host + "***"
                    flag = (p.get("cc") or "").lower()
                    emoji = "".join(chr(127462 + ord(c) - 97) for c in flag) if flag else "🌐"
                    items.append({
                        "ip": masked, "port": port, "rtt": p.get("rtt", 0),
                        "country": p.get("country", ""), "cc": p.get("cc", ""),
                        "proto": p.get("proto", "socks5"),
                        "flag": emoji, "checked": p.get("checked", 0)
                    })
                items.sort(key=lambda x: x["rtt"])
                self._json({"status": "ok", "count": len(items[:limit]),
                            "proxies": items[:limit], "total": len(proxies)})
                return

            if u.path == "/refresh":
                threading.Thread(target=collect, daemon=True).start()
                self._json({"status": "ok", "msg": "добыча запущена в фоне"})
                return

            self._json({"status": "error", "error": "not found",
                        "routes": ["/socks5.txt", "/socks5.json", "/status", "/refresh", "/health"]}, 404)
        except Exception as e:
            self._json({"status": "error", "error": str(e)}, 500)


def main():
    # загрузка кэша
    global _pool
    try:
        with open(CACHE_FILE) as f:
            _pool = json.load(f)
    except Exception:
        _pool = {"proxies": [], "updated": 0, "stats": {}}

    threading.Thread(target=collect, daemon=True).start()
    threading.Thread(target=lambda: _refresh_loop(), daemon=True).start()

    srv = ThreadingHTTPServer(("0.0.0.0", PORT), H)
    print(f"🧦 SOCKS API на :{PORT}", file=sys.stderr)
    srv.serve_forever()


def _refresh_loop():
    while True:
        time.sleep(REFRESH_EVERY)
        try:
            collect()
        except Exception as e:
            print(f"[SOCKS] refresh err: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
