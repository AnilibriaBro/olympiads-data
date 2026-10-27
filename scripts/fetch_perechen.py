"""Скачивает таблицу перечня олимпиад с rsr-olymp.ru в scripts/rsosh_rows.json.

Usage: python scripts/fetch_perechen.py
"""
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
root = Path(__file__).resolve().parent


def download(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(4):
        try:
            return urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "replace")
        except OSError:
            if attempt == 3:
                raise
            time.sleep(5)


page = download("https://rsr-olymp.ru/")
table = page[page.find("<table"):]
rows = []
for tr in re.findall(r"<tr.*?</tr>", table, re.S)[2:]:
    cells = [re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", c))).strip()
             for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
    links = re.findall(r'href="([^"]+)"', tr)
    if len(cells) in (3, 5):
        rows.append({"c": cells, "l": links[:1]})

# Защита от поломки сайта: в перечне всегда десятки олимпиад
olympiads = sum(1 for r in rows if len(r["c"]) == 5)
if olympiads < 30:
    raise SystemExit(f"Подозрительно мало олимпиад ({olympiads}), таблица на сайте могла измениться")

(root / "rsosh_rows.json").write_text(json.dumps(rows, ensure_ascii=False, indent=0), encoding="utf-8")
print("rows:", len(rows), "olympiad rows:", olympiads)
