"""Проверка данных приложения перед выпуском: дубли, битые ссылки между списками, пустые поля.

Запуск: python scripts/check_data.py — печатает найденные ошибки, код выхода 1, если они есть.
"""
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
scripts = Path(__file__).resolve().parent
sys.path.insert(0, str(scripts))
from names import norm_name  # noqa: E402

src = scripts.parent / "src" / "data"
errors = []


def err(msg):
    errors.append(msg)


def load(name):
    return json.loads((src / name).read_text(encoding="utf-8"))


per = load("perechen.json")
extra = load("extra.json")
mp = load("minpros.json")
dates = load("dates.json")
ts = (src / "vuzes.ts").read_text(encoding="utf-8")
manual = dict(re.findall(r"id: '([^']+)', short: '[^']+', name: '([^']+)'", ts))
URL = re.compile(r"^https?://[^\s]+$")
DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Вузы: id без повторов, у каждого есть город, названия не повторяются
vuz_ids = set(manual)
names = {norm_name(n): i for i, n in manual.items()}
for v in mp["vuzes"]:
    if v["id"] in vuz_ids:
        err(f"вуз: повтор id {v['id']}")
    vuz_ids.add(v["id"])
    if not v.get("city"):
        err(f"вуз без города: {v['name']}")
    k = norm_name(v["name"])
    if k in names:
        err(f"вуз записан дважды: {v['name']} ({names[k]} и {v['id']})")
    names[k] = v["id"]

# Справочник вузов из мониторинга: без повторов с теми, что уже есть, у филиала есть головной вуз
vdir = load("vuzdir.json")
if len(vdir["items"]) < 300:
    err(f"справочник вузов: всего {len(vdir['items'])} — мало")
for v in vdir["items"]:
    if v["id"] in vuz_ids:
        err(f"справочник вузов: повтор id {v['id']} ({v['name'][:60]})")
    if not v.get("city"):
        err(f"справочник вузов: без города {v['name'][:60]}")
    k = (norm_name(v["name"]), v["city"])
    if k in names:
        err(f"справочник вузов: записан дважды {v['name'][:60]}")
    names[k] = v["id"]
    vuz_ids.add(v["id"])
for v in vdir["items"] + vdir["known"]:
    if v.get("parent") and v["parent"] not in vuz_ids:
        err(f"справочник вузов: неизвестный головной вуз {v['parent']} у {v['id']}")
for k in vdir["known"]:
    if k["id"] not in vuz_ids:
        err(f"справочник вузов: неизвестный вуз {k['id']}")

# Перечень РСОШ
nums = [o["num"] for o in per]
if len(nums) != len(set(nums)):
    err("перечень РСОШ: повторяются номера")
seen = {}
for o in per:
    k = norm_name(o["name"])
    if k in seen:
        err(f"перечень РСОШ: олимпиада дважды — №{seen[k]} и №{o['num']}")
    seen[k] = o["num"]
    if not o["profiles"]:
        err(f"перечень РСОШ №{o['num']}: нет профилей")
    if o.get("url") and not URL.match(o["url"]):
        err(f"перечень РСОШ №{o['num']}: странная ссылка {o['url']}")

# Даты этапов
for k, d in dates.items():
    for s in d.get("stages", []):
        for f in ("start", "end"):
            if s.get(f) and not DAY.match(s[f]):
                err(f"даты №{k}: неверная дата {s[f]}")
        if s.get("start") and s.get("end") and s["start"] > s["end"]:
            err(f"даты №{k}: «{s['name']}» кончается раньше, чем начинается")

# «Баллы в вузах»
ids = [e["id"] for e in extra["items"]]
if len(ids) != len(set(ids)):
    err("баллы в вузах: повторяются id")
seen = {}
for e in extra["items"]:
    k = norm_name(e["name"])
    if k in seen:
        err(f"баллы в вузах: олимпиада дважды — {seen[k]} и {e['id']}")
    seen[k] = e["id"]
    if e.get("site") and not URL.match(e["site"]):
        err(f"баллы в вузах {e['id']}: странная ссылка {e['site']}")
    pairs = set()
    for b in e["benefits"]:
        if b["vuz"] not in manual:
            err(f"баллы в вузах {e['id']}: неизвестный вуз {b['vuz']}")
        if not URL.match(b.get("source", "")):
            err(f"баллы в вузах {e['id']}/{b['vuz']}: нет ссылки на официальный документ")
        if not b.get("text"):
            err(f"баллы в вузах {e['id']}/{b['vuz']}: пустой текст льготы")
        if b["vuz"] in pairs:
            err(f"баллы в вузах {e['id']}: вуз {b['vuz']} указан дважды")
        pairs.add(b["vuz"])
for p in extra["participation"]:
    if p["vuz"] not in manual:
        err(f"правило участия: неизвестный вуз {p['vuz']}")
    for n in p["perechen"] if isinstance(p["perechen"], list) else []:  # "all" — все олимпиады перечня
        if n not in nums:
            err(f"правило участия {p['vuz']}: нет олимпиады №{n} в перечне")

# Перечень Минпросвещения
mids = [m["id"] for m in mp["items"]]
if len(mids) != len(set(mids)):
    err("перечень Минпроса: повторяются id")
extra_ids = set(ids)
for m in mp["items"]:
    if not m["name"].strip():
        err(f"перечень Минпроса {m['n']}: пустое название")
    if m.get("vuzId") and m["vuzId"] not in vuz_ids:
        err(f"перечень Минпроса {m['n']}: неизвестный вуз {m['vuzId']}")
    if m["vuz"] and not m.get("vuzId"):
        err(f"перечень Минпроса {m['n']}: проводит вуз, но он не определён")
    same = m.get("same") or {}
    if "extra" in same and same["extra"] not in extra_ids:
        err(f"перечень Минпроса {m['n']}: ссылка на несуществующую запись {same['extra']}")
for e in extra["items"]:
    if e.get("minpros") and not any(m["name"] == e["minpros"] for m in mp["items"]):
        err(f"баллы в вузах {e['id']}: в перечне Минпроса нет «{e['minpros'][:60]}»")
# Одна и та же олимпиада не должна показываться дважды
shown = {}
for m in mp["items"]:
    if m.get("same"):
        continue
    k = (m["name"].strip().lower(), m["profile"], m["org"])  # точное название: XXI и XXII тур — разные
    if k in shown:
        err(f"перечень Минпроса: дубль {shown[k]} и {m['n']}")
    shown[k] = m["n"]

unique = sum(1 for m in mp["items"] if not m.get("same"))
print(f"перечень РСОШ: {len(per)}, баллы в вузах: {len(extra['items'])}, "
      f"перечень Минпроса: {unique} (всего {len(mp['items'])}), вузов и филиалов: {len(vuz_ids)}")
if errors:
    print(f"НАЙДЕНО ОШИБОК: {len(errors)}")
    for e in errors:
        print(" -", e)
    sys.exit(1)
print("ошибок нет")
