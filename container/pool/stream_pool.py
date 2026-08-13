#!/usr/bin/env python3
"""
stream_pool.py — ПОТОКОВАЯ добыча и обновление SOCKS5-пула.

Главное отличие от socks_api.collect(): НЕ ждём валидации всех кандидатов.
Живые прокси добавляются в пул СРАЗУ, по мере проверки (потоково).
Пул-файл перезаписывается каждые N секунд → ротатор всегда видит свежих.

Потоки:
  - fetcher: тянет списки прокси из источников (GitHub + API), кладёт в очередь
  - workers (100): берут кандидата, валидируют (CONNECT + HTTP), живой → в пул
  - persister: каждые 10 c пишет пул в файл
  - reaper: раз в 300 c перепроверяет прокси из пула, мёртвых убирает
  - refresh: раз в 300 c заново запускает fetch (всегда свежие)
"""
import concurrent.futures
import json
import os
import random
import re
import socket
import sys
import threading
import time
import urllib.request

POOL_FILE = os.environ.get("POOL_FILE", "/output/socks5_pool.json")
SEED_DIR = os.environ.get("SEED_DIR", "/app/seed")
FETCH_EVERY = int(os.environ.get("FETCH_EVERY", "300"))     # перезапуск добычи
PERSIST_EVERY = int(os.environ.get("PERSIST_EVERY", "10"))  # запись пула
REAP_EVERY = int(os.environ.get("REAP_EVERY", "300"))       # перепроверка пула
MAX_POOL = int(os.environ.get("MAX_POOL", "3000"))          # верхний лимит пула
VALIDATE_TIMEOUT = int(os.environ.get("VALIDATE_TIMEOUT", "6"))

SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/socks5.txt",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/socks5.txt",
    "https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt",
    "https://raw.githubusercontent.com/sunny9577/proxy-scraper/master/proxies.txt",
    "https://raw.githubusercontent.com/clarketm/proxy-list/master/proxy-list-raw.txt",
    "https://raw.githubusercontent.com/rdavydov/proxy-list/main/proxies/socks5.txt",
    "https://api.proxyscrape.com/v2/?request=getproxies&protocol=socks5&timeout=10000&country=all&ssl=all&anonymity=all",
    "https://api.proxyscrape.com/v3/free-proxy-list/get?request=displayproxies&protocol=socks5&proxy_format=ipport&format=text&timeout=10000",
]

_lock = threading.Lock()
_queue = []            # кандидаты на проверку (list, FIFO)
_in_queue = set()      # для дедупликации очереди
_pool: dict = {}       # proxy -> {"proxy","rtt","checked","country","cc","fails"}
_fetched = 0
_checked = 0
_last_error = ""


# ─── fetch ────────────────────────────────────────────────────────

def _fetch_raw(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as r:
            txt = r.read().decode("utf-8", "replace")
        out = []
        for line in txt.splitlines():
            line = line.strip()
            m = re.match(r"^([\d.]+):(\d{2,5})$", line)
            if m:
                out.append(f"{m.group(1)}:{m.group(2)}")
        return out
    except Exception:
        return []


def _seed():
    """Сид из локальных кэшей — мгновенный старт без ожидания сети."""
    found = []
    if os.path.isdir(SEED_DIR):
        for fn in os.listdir(SEED_DIR):
            if not fn.endswith(".json"):
                continue
            try:
                d = json.load(open(os.path.join(SEED_DIR, fn)))
                for p in d.get("proxies", []):
                    if p.get("alive") and p.get("proto") == "socks5" and ":" in str(p.get("proxy", "")):
                        found.append(p["proxy"])
            except Exception:
                continue
    return found


def fetch_loop():
    global _fetched, _last_error
    while True:
        try:
            print("[pool] fetch round start", file=sys.stderr, flush=True)
            chunks = []
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
                res = list(ex.map(_fetch_raw, SOURCES))
            cands = _seed()
            for chunk in res:
                cands += chunk
            cands = list(dict.fromkeys(cands))
            random.shuffle(cands)
            with _lock:
                for c in cands:
                    if c in _pool:
                        continue
                    if c not in _in_queue:
                        _queue.append(c)
                        _in_queue.add(c)
                _fetched = len(cands)
            print(f"[pool] fetched {len(cands)} cands (seed+net), queued {len(_queue)}", file=sys.stderr, flush=True)
        except Exception as e:
            _last_error = str(e)
            print(f"[pool] fetch err: {e}", file=sys.stderr, flush=True)
        time.sleep(FETCH_EVERY)


# ─── validation ───────────────────────────────────────────────────

def _geo(ip):
    try:
        import urllib.request as _ur
        with _ur.urlopen(f"http://ip-api.com/json/{ip}?fields=countryCode,country", timeout=5) as r:
            d = json.loads(r.read())
            return d.get("countryCode", ""), d.get("country", "")
    except Exception:
        return "", ""


def _try(proxy):
    try:
        h, p = proxy.rsplit(":", 1)
        import socks
        s = socks.socksocket()
        s.set_proxy(socks.SOCKS5, h, int(p))
        s.settimeout(VALIDATE_TIMEOUT)
        t0 = time.time()
        s.connect(("api.ipify.org", 80))
        s.send(b"GET / HTTP/1.0\r\nHost: api.ipify.org\r\n\r\n")
        data = b""
        while True:
            c = s.recv(2048)
            if not c:
                break
            data += c
            if len(data) > 4096:
                break
        s.close()
        body = data.split(b"\r\n\r\n")[-1].decode("utf-8", "replace").strip()
        ok = bool(data) and bool(re.match(r"^\d{1,3}(\.\d{1,3}){3}$", body))
        return (ok, int((time.time() - t0) * 1000), body if ok else "")
    except Exception:
        return (False, 0, "")


def worker_loop():
    global _checked
    while True:
        proxy = None
        with _lock:
            while _queue:
                c = _queue.pop(0)
                _in_queue.discard(c)
                if c not in _pool:
                    proxy = c
                    break
            _checked += 1 if proxy else 0
        if not proxy:
            time.sleep(0.2)
            continue
        ok, rtt, ip = _try(proxy)
        if ok:
            with _lock:
                if len(_pool) >= MAX_POOL:
                    continue
                cc, cn = _geo(ip.split(":")[0] if ":" in ip else ip)
                _pool[proxy] = {"proxy": proxy, "proto": "socks5", "rtt": rtt,
                                "alive": True, "checked": int(time.time()),
                                "country": cn, "cc": cc}
            print(f"[pool] + alive {proxy} ({rtt}ms)", file=sys.stderr, flush=True)


def reaper_loop():
    """Перепроверка пула: мёртвые убираем, чтобы не тратить время ротатора."""
    while True:
        time.sleep(REAP_EVERY)
        with _lock:
            snap = list(_pool.keys())
        if not snap:
            continue
        dead = []
        for proxy in snap:
            ok, _, _ = _try(proxy)
            if not ok:
                dead.append(proxy)
        with _lock:
            for p in dead:
                _pool.pop(p, None)
        print(f"[pool] reaper: {len(dead)} dead removed, pool={len(_pool)}", file=sys.stderr, flush=True)


def persister_loop():
    while True:
        time.sleep(PERSIST_EVERY)
        with _lock:
            proxies = sorted(_pool.values(), key=lambda x: x.get("rtt", 9999))
        data = {"proxies": proxies, "updated": int(time.time()),
                "stats": {"total": len(proxies), "sources": len(SOURCES), "country": "all"}}
        try:
            with open(POOL_FILE, "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"[pool] persist err: {e}", file=sys.stderr, flush=True)


def main():
    threads = [threading.Thread(target=fetch_loop, daemon=True)]
    for _ in range(int(os.environ.get("WORKERS", "100"))):
        threads.append(threading.Thread(target=worker_loop, daemon=True))
    threads += [
        threading.Thread(target=reaper_loop, daemon=True),
        threading.Thread(target=persister_loop, daemon=True),
    ]
    for t in threads:
        t.start()
    # сид: НЕ кладём в пул вслепую — отправляем в очередь на проверку (живые попадут в пул)
    with _lock:
        for p in _seed():
            if p not in _pool and p not in _in_queue:
                _queue.append(p)
                _in_queue.add(p)
    print(f"[pool] stream_pool started. seed queued={len(_seed())}, persist={PERSIST_EVERY}s", file=sys.stderr, flush=True)
    while True:
        time.sleep(60)
        with _lock:
            n = len(_pool)
        print(f"[pool] status: pool={n}, fetched={_fetched}, checked={_checked}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
