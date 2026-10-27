"""Сводит даты с olimpiada.ru (scripts/olimpiada_ru_events.json) в этапы для приложения.

Usage: python scripts/fetch_dates.py && python scripts/build_dates.py
Результат: src/data/dates.json — {номер в перечне: {act, stages, note}}.
"""
import json
import re
import sys
import html
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
root = Path(__file__).resolve().parent

# Номер олимпиады в перечне РСОШ 2026/27 -> id страницы на olimpiada.ru
ACT = {
    1: 177, 2: 6945, 3: 5369, 4: 5854, 5: 5825, 6: 22, 7: 182, 8: 5864, 9: 5150, 10: 5429,
    11: 125, 12: 5022, 13: 282, 14: 57, 15: 199, 16: 5237, 17: 5795, 18: 5003, 19: 5392, 20: 193,
    21: 6949, 22: 322, 23: 203, 24: 240, 25: 5018, 26: 130, 27: 58, 28: 194, 29: 6943, 30: 257,
    31: 5005, 32: 234, 33: 176, 34: 5457, 35: 146, 36: 5332, 37: 357, 38: 123, 39: 196, 40: 4337,
    41: 5371, 42: 5006, 43: 233, 44: 5726, 45: 66, 46: 237, 47: 5177, 48: 23, 49: 243, 50: 5353,
    51: 5516, 52: 201, 53: 5011, 54: 244, 57: 206, 58: 5, 59: 4, 60: 249,
}

SKIP = ("тренировоч", "подготовит", "результат", "апелляц", "балл", "разбор", "показ", "публикац", "итог", "награжд", "закрыт")
_today = date.today()
SEASON = _today.year if _today.month >= 8 else _today.year - 1
SEASON_START = f"{SEASON}-08-15"


def kind(name):
    n = name.lower()
    if any(w in n for w in SKIP):
        return None
    if "регистрац" in n:
        return "Регистрация"
    if "заочн" in n or "полуфинал" in n or "отбор" in n:
        return "Отборочный этап"
    if "заключ" in n or "финал" in n or re.search(r"(^|\s)очный тур", n):
        return "Заключительный этап"
    if "отбор" in n or "тур" in n or "этап" in n or "дистанц" in n or "онлайн" in n:
        return "Отборочный этап"
    return None


def status_note(act):
    f = root / "cache" / f"activity_{act}.html"
    if not f.exists():
        return ""
    m = re.search(r'<div class="tc-status">\s*<a[^>]*>(.*?)</a>', f.read_text(encoding="utf-8"), re.S)
    if not m:
        return ""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", m.group(1)))).replace("→", "").strip()


def main():
    pages = {p["act"]: p for p in json.loads((root / "olimpiada_ru_events.json").read_text(encoding="utf-8"))}
    out = {}
    for num, act in ACT.items():
        page = pages.get(act)
        if not page:
            continue
        spans = {}
        for ev in page["events"]:
            k = kind(ev["name"])
            if not k or ev["end"] < SEASON_START:
                continue
            s, e = spans.get(k, (None, None))
            start = ev["start"] or ev["end"]
            spans[k] = (min(s, start) if s else start, max(e, ev["end"]) if e else ev["end"])
        order = ["Регистрация", "Отборочный этап", "Заключительный этап"]
        stages = [{"name": k, "start": spans[k][0], "end": spans[k][1]} for k in order if k in spans]
        # «До 30 ноя» без даты начала: регистрация считается открытой с начала сезона
        for st in stages:
            if st["name"] == "Регистрация" and st["start"] == st["end"] and any(
                    ev["start"] is None for ev in page["events"] if kind(ev["name"]) == "Регистрация"):
                st["start"] = f"{SEASON}-09-01"
        out[num] = {"act": act, "stages": stages, "note": status_note(act)}
        print(num, act, [(s["name"][:5], s["start"], s["end"]) for s in stages], out[num]["note"][:50])

    (root.parent / "src" / "data" / "dates.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("with dates:", sum(1 for v in out.values() if v["stages"]), "of", len(ACT))


if __name__ == "__main__":
    main()
