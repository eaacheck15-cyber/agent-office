#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Извлечение ценных строк из артефактов офиса в SQLite-БД (loot.db).
Сканирует ./output и ./scam-projects: ключи, токены, IP, домены, эндпоинты,
email, строки подключения, конфиги. Только уже собранные открытые данные.

ПРАВИЛО ЦЕННОСТИ (владелец): в БД только то, что имеет денежную/операционную
ценность ($$$$/$$$/$$/$). Мусор (шаблоны, парковки, ложные regex) — отбрасывается.
"""
import os
import re
import sqlite3
import json

ROOT = "/root/office"
OUT = os.path.join(ROOT, "output")
DB = os.path.join(OUT, "loot.db")
SKIP_EXT = {".py", ".db", ".age", ".png", ".ico", ".jpg", ".gif", ".svg", ".woff", ".woff2", ".ttf", ".css", ".map"}
SKIP_DIRS = {".git", "container", ".opencode", "agents-source", "pinterest-growth-agent", "mcp", "node_modules"}

def files():
    for base in (OUT, os.path.join(ROOT, "scam-projects")):
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in filenames:
                ext = os.path.splitext(fn)[1].lower()
                if ext in SKIP_EXT:
                    continue
                if fn.startswith("loot.db"):
                    continue
                p = os.path.join(dirpath, fn)
                try:
                    if os.path.getsize(p) > 3_000_000:  # слишком большие бандлы — только выборочно
                        continue
                    yield p
                except OSError:
                    continue

RE_KEYS = {
    "api_key": re.compile(r"(?i)\b(api[_-]?key|apikey|api_key)\b\s*[=:]\s*[\"']?([A-Za-z0-9_\-]{12,})"),
    "token": re.compile(r"\beyJ[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{20,}\.[A-Za-z0-9_\-]{10,}"),
    "secret": re.compile(r"(?i)\b(secret|client[_-]?secret|private[_-]?key)\b\s*[=:]\s*[\"']?([A-Za-z0-9_\-+/=]{12,})"),
    "ga": re.compile(r"\bG-[A-Z0-9]{6,12}\b"),
    "amp": re.compile(r"\b[0-9a-f]{32}\b"),
    "connstr": re.compile(r"(?i)(Server=|Data Source=|Initial Catalog=|User ID=|Password=|Integrated Security=)[^\"'\s,;]{3,}"),
    "email": re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"),
    "ip": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "endpoint": re.compile(r'"/(?:api/|AdminManagement/|Clients/|Affiliate/|Accounts/|generic/|public/|auth/|funds/|Payment/)[A-Za-z0-9/_.\-]{3,}"'),
    "domain": re.compile(r"\b[a-z0-9][a-z0-9\-]{1,60}\.(?:com|net|org|io|pl|md|by|in|eu|de|fr|uk|ru|it|es|hu|pt|tr|nl|ro|cz)\b"),
}

# JS-мусорные маркеры: если connstr содержит код, это ложное срабатывание минификатора
JS_GARBAGE = ("dispose", "function", "partialObserver", "{const", "}const", "return", "=>", "this.", "e=>",
              "n=>", "t=>", "new ", ".bind(", "apply(", "call(", "0x", "_0x", "true", "false", "null",
              "===t.", "===", "password===t", "server=r}", "server=Q}", "server=n}",
              "server=new", "oldpassword", ".oldpassword", "password=p.", "p.oldpassword")

def _looks_real_connstr(v):
    """Настоящая строка подключения: без JS-кода, с именем сервера/параметрами."""
    low = v.lower()
    for m in JS_GARBAGE:
        if m.lower() in low:
            return False
    # минимум 3 символа после префикса и не похоже на оператор
    if len(v) < 5:
        return False
    return True

def main():
    if os.path.exists(DB):
        os.remove(DB)
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS secrets (type TEXT, value TEXT, source TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS endpoints (value TEXT, source TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS hosts (value TEXT, source TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS emails (value TEXT, source TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS ips (value TEXT, source TEXT)")
    c.execute("CREATE TABLE IF NOT EXISTS configs (value TEXT, source TEXT)")

    counts = {"api_key": 0, "token": 0, "secret": 0, "ga": 0, "amp": 0, "connstr": 0,
              "email": 0, "ip": 0, "endpoint": 0, "domain": 0}
    seen = {k: set() for k in counts}
    domain_skip = {"github.com", "googleapis.com", "gstatic.com", "jsdelivr.net", "cloudflare.com",
                   "google.com", "w3.org", "apple.com", "facebook.com", "amazonaws.com", "reactjs.org",
                   "fontawesome.com", "bootstrapcdn.com", "wordpress.org", "wordpress.com", "intercom.io"}

    for path in files():
        rel = path.replace(ROOT + "/", "")
        try:
            with open(path, "r", errors="ignore", encoding="utf-8") as f:
                data = f.read()
        except OSError:
            continue
        if len(data) < 12:
            continue
        for k, rx in RE_KEYS.items():
            for m in rx.finditer(data):
                val = m.group(0).strip().strip('"').strip("'")
                if len(val) > 120:
                    continue
                if k == "domain" and val.split(".")[-1] in ("png", "jpg", "css", "js", "svg"):
                    continue
                if k == "domain" and val in domain_skip:
                    continue
                if k == "ip":
                    parts = val.split(".")
                    if any(int(p) > 255 for p in parts):
                        continue
                if k == "connstr" and not _looks_real_connstr(val):
                    continue
                if val in seen[k]:
                    continue
                seen[k].add(val)
                counts[k] += 1
                if k in ("api_key", "token", "secret", "ga", "amp", "connstr"):
                    c.execute("INSERT INTO secrets (type, value, source) VALUES (?,?,?)", (k, val, rel))
                elif k == "email":
                    c.execute("INSERT INTO emails (value, source) VALUES (?,?)", (val, rel))
                elif k == "ip":
                    c.execute("INSERT INTO ips (value, source) VALUES (?,?)", (val, rel))
                elif k == "endpoint":
                    c.execute("INSERT INTO endpoints (value, source) VALUES (?,?)", (val.strip('"'), rel))
                elif k == "domain":
                    c.execute("INSERT INTO hosts (value, source) VALUES (?,?)", (val, rel))

    conn.commit()
    print("=== ИТОГО (уникальных ценных строк) ===")
    for k, v in counts.items():
        print(f"{k:10} {v}")
    for t in ("secrets", "endpoints", "hosts", "emails", "ips"):
        n = c.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"таблица {t}: {n}")
    conn.close()

if __name__ == "__main__":
    main()
