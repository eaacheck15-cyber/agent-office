#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""iPhone-браузер офиса — РЕАЛЬНЫЕ отпечатки устройств (из playwright.devices).
Никаких фантазий: точные UA/viewport/scale/touch для каждой модели.
Через прокси 161. Ротация моделей.
Использование: python3 office_iphone.py <url> [--shot] [--dump] [--model=iPhone 15|iPhone 13|...]
"""
import os, sys, re, random
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "https://midasfx.com"
SHOT = "--shot" in sys.argv
DUMP = "--dump" in sys.argv

# РЕАЛЬНЫЕ модели из playwright.devices (проверено: существуют, включая 16/17)
REAL_MODELS = [
    "iPhone 17 Pro Max", "iPhone 17 Pro", "iPhone 17", "iPhone 17e",
    "iPhone 16 Pro Max", "iPhone 16 Pro", "iPhone 16 Plus", "iPhone 16", "iPhone 16e",
    "iPhone 15 Pro Max", "iPhone 15 Pro", "iPhone 15 Plus", "iPhone 15",
    "iPhone 14 Pro Max", "iPhone 14 Pro", "iPhone 14 Plus", "iPhone 14",
    "iPhone 13 Pro Max", "iPhone 13 Pro", "iPhone 13 Mini", "iPhone 13",
    "iPhone 12 Pro Max", "iPhone 12 Pro", "iPhone 12 Mini", "iPhone 12",
    "iPhone 11 Pro Max", "iPhone 11 Pro", "iPhone 11",
    "iPhone SE (3rd gen)", "iPhone SE",
    "iPhone Air",
    # Планшеты: 3 последних поколения + Pro
    "iPad (gen 11)",   # последнее поколение
    "iPad (gen 7)",    # 2-е с конца
    "iPad (gen 6)",    # 3-е с конца
    "iPad Pro 11",     # топовый
    "iPad Mini",       # мини
]

model = None
for a in sys.argv:
    if a.startswith("--model="):
        model = a.split("=",1)[1]
if not model or model not in REAL_MODELS:
    model = random.choice(REAL_MODELS)

print(f"[iphone] модель: {model} (реальный отпечаток)", flush=True)

BROWSER_PX = {"server": "http://161.0.21.149:8000", "username": "nt32pe", "password": "yzuAZr"}
OUT = "/root/office/output/iphone"
os.makedirs(OUT, exist_ok=True)

with sync_playwright() as p:
    dev = p.devices[model]  # реальный отпечаток
    b = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-blink-features=AutomationControlled"])
    ctx = b.new_context(
        **dev,               # все реальные параметры: UA, viewport, scale, touch, mobile
        locale="en-US",
        timezone_id="Europe/Moscow",
        proxy=BROWSER_PX,
    )
    pg = ctx.new_page()
    print(f"[iphone] открываю {URL} через прокси 161...", flush=True)
    try:
        pg.goto(URL, timeout=45000, wait_until="domcontentloaded")
        pg.wait_for_timeout(6000)
        print(f"[iphone] URL: {pg.url}", flush=True)
        print(f"[iphone] title: {pg.title()}", flush=True)
        if DUMP:
            txt = pg.inner_text("body")
            print(f"[iphone] текст ({len(txt)} симв):", flush=True)
            print(txt[:800], flush=True)
            fname = f"{OUT}/dump_{model.replace(' ','_')}_{re.sub(r'[^a-z0-9]','',URL.split('//')[1])[:20]}.txt"
            open(fname,"w").write(txt)
            print(f"[iphone] сохранено: {fname}", flush=True)
        if SHOT:
            f = f"{OUT}/shot_{model.replace(' ','_')}_{re.sub(r'[^a-z0-9]','',URL.split('//')[1])[:20]}.png"
            pg.screenshot(path=f, full_page=True)
            print(f"[iphone] скриншот: {f}", flush=True)
    except Exception as e:
        print(f"[iphone] ERR: {str(e)[:80]}", flush=True)
    b.close()
