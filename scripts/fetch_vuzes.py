"""Скачивает список всех вузов и филиалов России из мониторинга Минобрнауки (monitoring.miccedu.ru)
в scripts/vuzes_rows.json: название, город, регион, номер в мониторинге.

Usage: python scripts/fetch_vuzes.py [--force]
Мониторинг обновляется раз в год, поэтому без --force список скачивается не чаще раза в 30 дней.
"""
import html
import http.client
import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
root = Path(__file__).resolve().parent
out = root / "vuzes_rows.json"
BASE = "https://monitoring.miccedu.ru/"

# Дата скачивания хранится в самом файле: при git checkout дата изменения файла всегда «сейчас»
if out.exists() and "--force" not in sys.argv:
    fetched = json.loads(out.read_text(encoding="utf-8")).get("fetched", 0)
    if time.time() - fetched < 30 * 86400:
        print("vuzes_rows.json свежий, пропускаю")
        sys.exit(0)


def download(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(6):
        try:
            return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
        except (OSError, http.client.HTTPException):  # сайт иногда обрывает длинные страницы
            if attempt == 5:
                raise
            time.sleep(5)


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


main = download(BASE + "?m=vpo")
regions = re.findall(r"href='(iam/(\d{4})/_vpo/material\.php\?type=2&id=(\d+))'>([^<]+)</a>", main)
year = max(r[1] for r in regions)
regions = [r for r in regions if r[1] == year]


def region_rows(r):
    path, _, _, region = r
    page = download(BASE + path)
    return [{"mid": int(m[1]), "city": clean(m[2]), "region": clean(region), "name": clean(m[3])}
            for m in re.finditer(r"<td id=(\d+)\s+icon='[^']*'\s+city='([^']*)'.*?class='inst'.*?<a href='inst\.php\?id=\d+'>(.*?)</a>", page, re.S)]


# Сайт отдаёт страницы медленно — качаем несколько регионов сразу
rows = []
with ThreadPoolExecutor(8) as pool:
    for i, part in enumerate(pool.map(region_rows, regions), 1):
        rows.extend(part)
        print(f"регион {i} из {len(regions)}", flush=True)

# Защита от поломки сайта: в мониторинге всегда больше тысячи вузов и филиалов
if len(rows) < 700:
    raise SystemExit(f"Мониторинг вернул только {len(rows)} вузов — похоже, сайт изменился")
out.write_text(json.dumps({"year": year, "fetched": int(time.time()), "rows": rows}, ensure_ascii=False, indent=0),
               encoding="utf-8")
print("регионов:", len(regions), "вузов и филиалов:", len(rows), "год мониторинга:", year)
