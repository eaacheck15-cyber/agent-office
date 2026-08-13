#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Многопоточный паук-краулер для ABET Global через пул SOCKS/HTTP прокси с ротацией.
Только разведка: GET-запросы, сбор URL/JS/форм/robots. Без эксплуатации."""
import re
import sys
import time
import urllib3
import requests
import concurrent.futures as cf

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HOSTS = [
    "abetglobal.com", "www.abetglobal.com", "uat.abetglobal.com",
    "testadmin.abetglobal.com", "eedmin.abetglobal.com", "manage.abetglobal.com",
    "secure.abetglobal.com", "www.secure.abetglobal.com", "staging.abetglobal.com",
    "forum.abetglobal.com", "api.abetglobal.com", "cmsapi.abetglobal.com",
    "crypto.abetglobal.com", "testmt5.abetglobal.com", "applicationapi.abetglobal.com",
]

PROXIES = [
    {"http": "socks5h://127.0.0.1:1080", "https": "socks5h://127.0.0.1:1080"},
    {"http": "socks5h://101.36.104.239:10808", "https": "socks5h://101.36.104.239:10808"},
    {"http": "socks5h://101.36.104.46:10808", "https": "socks5h://101.36.104.46:10808"},
    {"http": "http://127.0.0.1:8081", "https": "http://127.0.0.1:8081"},
]

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
    """GET с ротацией прокси. Возвращает (status, content_type, body) или (0, None, None)."""
    proxy = next_proxy()
    try:
        r = requests.get(url, proxies=proxy, headers={"User-Agent": UA,
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"}, verify=False, timeout=TIMEOUT,
            allow_redirects=True)
        return (r.status_code, (r.headers.get('Content-Type') or '').lower(), r.text)
    except Exception:
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

def main():
    out_urls = "/root/office/output/abet_spider_urls.txt"
    out_js = "/root/office/output/abet_spider_js.txt"
    out_forms = "/root/office/output/abet_spider_forms.txt"
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
    print("\n=== ИТОГО ===")
    print(f"URL: {len(all_urls)} | JS: {len(all_js)} | FORM: {len(all_forms)}")
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
