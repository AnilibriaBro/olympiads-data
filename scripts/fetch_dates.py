"""Собирает даты этапов олимпиад с olimpiada.ru и сохраняет в scripts/olimpiada_ru_events.json.

Usage: python scripts/fetch_dates.py
Страницы кэшируются в scripts/cache/ на CACHE_HOURS часов (по умолчанию 12, 0 — качать всё заново).
"""
import os
import json
import re
import sys
import time
import html
import urllib.request
from datetime import date, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
root = Path(__file__).resolve().parent
cache = root / "cache"
cache.mkdir(exist_ok=True)


def get(path):
    f = cache / (re.sub(r"\W+", "_", path).strip("_") + ".html")
    max_age = float(os.environ.get("CACHE_HOURS", "12")) * 3600
    if f.exists() and time.time() - f.stat().st_mtime < max_age:
        return f.read_text(encoding="utf-8")
    req = urllib.request.Request("https://olimpiada.ru" + path, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(4):
        try:
            text = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
            break
        except OSError:
            if attempt == 3:
                raise
            time.sleep(3)
    f.write_text(text, encoding="utf-8")
    time.sleep(0.5)
    return text


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


EVENT = re.compile(
    r'<div class="tl_event[^"]*" date="(\d{4}-\d{2}-\d{2})" ev_id="(\d+)" ev_act="(\d+)" length="(\d+)".*?'
    r'<span class="tl_cont_f"[^>]*>.*?<font[^>]*>(.*?)</font>', re.S)


MONTHS = {"сен": 9, "окт": 10, "ноя": 11, "дек": 12, "янв": 1, "фев": 2, "мар": 3,
          "апр": 4, "мая": 5, "май": 5, "июн": 6, "июл": 7, "авг": 8}
ROW = re.compile(r'<div class="event_name">(.*?)</div>.*?<td colspan="1">(.*?)</td>', re.S)


# Учебный год начинается в сентябре: осенние месяцы — этого года, весенние — следующего.
_today = date.today()
SEASON = _today.year if _today.month >= 8 else _today.year - 1


def season_date(d, mon):
    m = MONTHS[mon[:3]]
    return date(SEASON if m >= 9 else SEASON + 1, m, int(d))


def parse_when(text):
    """'До 30 ноя', '6 мар', '16...20 окт', '31 авг...22 сен' -> (start, end); start None для «До»."""
    t = text.replace("\xa0", " ").strip()
    until = t.lower().startswith("до")
    parts = re.findall(r"(\d{1,2})\s*([а-я]{3})?", t)
    parts = [(d, m) for d, m in parts]
    if not parts:
        return None
    # месяц у первой даты может быть опущен: «16...20 окт»
    last_m = parts[-1][1]
    if not last_m:
        return None
    filled = [(d, m or last_m) for d, m in parts]
    end = season_date(*filled[-1])
    start = None if until else season_date(*filled[0])
    return start, end


def table_events(page):
    i = page.find('<table class="events_for_activity">')
    if i < 0:
        return []
    block = page[i:page.find("</table>", i)]
    out = []
    for name, when in ROW.findall(block):
        parsed = parse_when(clean(when))
        if parsed:
            s, e = parsed
            out.append({"act": 0, "name": clean(name), "start": str(s) if s else None, "end": str(e)})
    return out


def events(page):
    out = {}
    for d, ev_id, act, length, name in EVENT.findall(page):
        start = date.fromisoformat(d)
        end = start + timedelta(days=max(int(length), 1) - 1)
        out[ev_id] = {"act": int(act), "name": clean(name), "start": str(start), "end": str(end)}
    return list(out.values())


# Список олимпиад перечня со ссылками на olimpiada.ru
article = get("/article/1266")
links = []
for act_id, title in re.findall(r'<a[^>]*href="/activity/(\d+)"[^>]*>(.*?)</a>', article, re.S):
    links.append({"act": int(act_id), "title": clean(title)})

# Страницы олимпиад перечня, которых нет в статье, добавляем по таблице соответствия
sys.path.insert(0, str(root))
from build_dates import ACT  # noqa: E402
known = {l["act"] for l in links}
links += [{"act": a, "title": ""} for a in ACT.values() if a not in known]

result = []
for link in links:
    page = get(f"/activity/{link['act']}")
    h1 = re.search(r"<h1>(.*?)</h1>", page, re.S)
    # У олимпиад с несколькими предметами — таймлайн по каждому предмету,
    # у одиночных — таблица «Расписание».
    evs = events(page) or table_events(page)
    result.append({**link, "h1": clean(h1.group(1)) if h1 else "", "events": evs})
    print(link["act"], len(evs), link["title"][:60])

(root / "olimpiada_ru_events.json").write_text(
    json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")
print("saved", len(result))
