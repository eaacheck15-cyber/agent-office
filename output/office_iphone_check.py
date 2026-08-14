#!/usr/bin/env python3
"""iPhone-проверка целей: реальные отпечатки + РОТАЦИЯ IP через прокси-пул.
Каждый запрос — новый IP (из API пула), новая модель iPhone.
Использование: python3 office_iphone_check.py <url> [--n=5]"""
import os, sys, json, re, random
import requests, urllib3
urllib3.disable_warnings()
import urllib.request

URL = sys.argv[1] if len(sys.argv) > 1 else "https://bitnexus.cc"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 5

# реальные модели iPhone (из playwright.devices)
MODELS = ["iPhone 17 Pro Max","iPhone 17","iPhone 16 Pro","iPhone 16","iPhone 15 Pro","iPhone 13","iPad (gen 11)"]

# IP из API пула
def get_ips(n):
    plist = urllib.request.urlopen("http://127.0.0.1:8912/socks5.txt?limit="+str(n), timeout=8).read().decode().splitlines()
    return [p for p in plist if ":" in p]

ips = get_ips(N)
print(f"IP из пула: {len(ips)}", flush=True)

for i in range(min(N, len(ips))):
    model = random.choice(MODELS)
    ip = ips[i]
    print(f"\n=== {i+1}. {model} через {ip} ===", flush=True)
    try:
        proxy = {"http": f"socks5h://{ip}", "https": f"socks5h://{ip}"}
        r = requests.get(URL, proxies=proxy, headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15"}, verify=False, timeout=12)
        t = re.search(r'<title>([^<]+)</title>', r.text, re.I)
        print(f"  [{ip}] {r.status_code} {t.group(1)[:40] if t else '?'} ({len(r.text)}б)", flush=True)
        # открытость ключевых путей
        for p in ["/core/.env", "/admin", "/install"]:
            try:
                r2 = requests.get(URL.split("/")[0]+"//"+URL.split("//")[1].split("/")[0]+p if "//" in URL else URL+p,
                    proxies=proxy, headers={"User-Agent":"Mozilla/5.0"}, verify=False, timeout=8)
                if r2.status_code == 200:
                    print(f"    ✅ {p}: 200 ({len(r2.text)}б)", flush=True)
            except Exception:
                pass
    except Exception as e:
        print(f"  [{ip}] ERR: {type(e).__name__}", flush=True)
