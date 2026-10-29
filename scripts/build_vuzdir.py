"""Справочник всех вузов и филиалов России для раздела «Вузы»: scripts/vuzes_rows.json (мониторинг
Минобрнауки) -> src/data/vuzdir.json.

Вузы, которые уже есть в приложении (src/data/vuzes.ts и организаторы перечня Минпросвещения), второй раз
не добавляются: им только дописывается регион. У филиала указан головной вуз — его олимпиады
показываются и на странице филиала.

Usage: python scripts/build_vuzdir.py
"""
import json
import re
import sys
import zlib
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
scripts = Path(__file__).resolve().parent
sys.path.insert(0, str(scripts))
from minpros_vuzes import KNOWN, canon  # noqa: E402

src = scripts.parent / "src" / "data"
raw = json.loads((scripts / "vuzes_rows.json").read_text(encoding="utf-8"))
for r in raw["rows"]:
    r["region"] = re.sub(r"^г\.\s*", "", r["region"])  # «г.Москва» -> «Москва»

# Духовные семинарии не принимают по ЕГЭ — в справочник для школьников не нужны
SKIP = re.compile(r"Религиозная организация|духовн|семинари", re.I)
BRANCH = re.compile(r"филиал", re.I)
CITY_PREFIX = re.compile(r"^(г\.|город|пос\.|п\.|пгт\.?|с\.|рп\.?|ст-ца|станица|д\.)\s*", re.I)
FEDERAL_CITIES = {"г. Москва": "Москва", "г. Санкт-Петербург": "Санкт-Петербург", "г. Севастополь": "Севастополь",
                  "Москва": "Москва", "Санкт-Петербург": "Санкт-Петербург", "Севастополь": "Севастополь"}


def key(name):
    """Название для сравнения: без «национальный исследовательский», «имени …», «при Правительстве …»,
    ведомства, скобок, кавычек и регистра."""
    s = name.lower().replace("ё", "е")
    s = re.sub(r"\b(им\.|имени)\s.*$", "", s)
    s = re.sub(r"\s(при|министерства|мид)\s.*$", "", s)
    s = re.sub(r"национальный исследовательский|\(.*?\)|[«»“”\"'.,]|\s[-–—]\s", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def look(d, k):
    """Поиск по названию, но не по одному слову: «университет» или «академия» — это не название вуза."""
    return d.get(k) if len(k.split()) >= 2 else None


def short_name(full):
    """Название вуза из строки мониторинга: то, что после «высшего образования», без почётных слов."""
    s = re.sub(r"^(Ордена [А-ЯЁа-яё ]+?Знамени|Министерства [а-яё ]+Российской Федерации)\s+", "", full.strip(), flags=re.I)
    m = re.search(r"высшего образования\s*(.+)$", s, re.I)
    if m:
        s = m.group(1)
    return canon(s).strip('"“”«» ')


def city_of(row):
    c = CITY_PREFIX.sub("", row["city"]).strip()
    return c or FEDERAL_CITIES.get(row["region"], row["region"])


def head_name(name):
    """Головной вуз из названия филиала: последнее название в кавычках или после «высшего образования»."""
    q = re.findall(r"[«\"“]([^«»\"“”]{6,})[»\"”]", name)
    if q:
        return canon(q[-1])
    m = re.search(r"высшего образования\s+(.+)$", name)
    return canon(m.group(1)) if m else ""


def branch_label(name):
    """Собственное название филиала: «Нижегородский филиал», «Саровский физико-технический институт»."""
    s = re.split(r"\s*[-–—]\s*филиал|\s*\(филиал\)", name, maxsplit=1, flags=re.I)[0]
    s = re.split(r"(?<=филиал)\s+(?=[А-ЯЁа-яё\"«])", s, maxsplit=1, flags=re.I)[0]  # «Нижегородский филиал федерального …»
    return s.strip(" -–—\"«»")


ts = (src / "vuzes.ts").read_text(encoding="utf-8")
manual = [dict(zip(("id", "short", "name", "city"), m))
          for m in re.findall(r"id: '([^']+)', short: '([^']+)', name: '([^']+)', city: '([^']+)'", ts)]
mp_vuzes = json.loads((src / "minpros.json").read_text(encoding="utf-8"))["vuzes"]
known = {}
for v in manual + mp_vuzes:
    known.setdefault(key(v["name"]), v["id"])
# Сокращённые и старые названия вузов, описанных вручную
ALIASES = {"московский физико-технический институт": "mipt", "московский государственный университет": "msu",
           "университет итмо": "itmo", "высшая школа экономики": "hse", "университет высшая школа экономики": "hse",
    "первый московский государственный медицинский университет": "sechenov",
    "технологический университет мисис": "misis", "университет науки и технологий мисис": "misis"}
for k, v in ALIASES.items():
    if any(m["id"] == v for m in manual):
        known.setdefault(k, v)

heads, branches, matched = {}, [], {}
for row in raw["rows"]:
    if SKIP.search(row["name"]):
        continue
    if BRANCH.search(row["name"]):
        branches.append(row)
        continue
    name = short_name(row["name"])
    k = key(name)
    vid = look(known, k) or "v" + format(zlib.crc32(name.lower().encode("utf-8")), "x")
    if vid in heads or vid in matched:
        continue
    if look(known, k):
        matched[vid] = {"id": vid, "region": row["region"], "mid": row["mid"]}
    else:
        heads[vid] = {"id": vid, "name": name, "city": city_of(row), "region": row["region"], "mid": row["mid"]}

items = list(heads.values())
heads_by_key = {key(v["name"]): v["id"] for v in items}
names_by_id = {v["id"]: v.get("short") if v.get("short") and len(v.get("short", "")) > 2 else v["name"] for v in manual + mp_vuzes + items}
lost = 0
for row in branches:
    label = branch_label(row["name"])
    head = head_name(row["name"])
    # Филиал, который сам проводит мероприятия перечня Минпросвещения, уже есть в приложении под своим названием
    own = look(known, key(label)) or look(known, key(canon(row["name"])))
    # Сначала — признаки вузов из vuzes.ts («Высшая школа экономики», «МИФИ»): в названиях филиалов кавычки вложенные
    rest = row["name"][len(label):]
    k = key(head)
    parent = (next((vid for pat, vid in KNOWN if re.search(pat.strip("^$"), rest)), None)
              or look(known, k) or look(heads_by_key, k))
    if own:
        matched.setdefault(own, {"id": own, "region": row["region"], "mid": row["mid"], **({"parent": parent} if parent and parent != own else {})})
        continue
    if not parent:
        lost += 1
    vid = "f" + format(zlib.crc32(str(row["mid"]).encode()), "x")
    head_title = names_by_id.get(parent, head)
    if label.lower().endswith("филиал") and len(label) > len("филиал"):
        title = f"{label} — {head_title}"  # «Нижегородский филиал — Высшая школа экономики»
    elif label.lower() in ("филиал", ""):
        title = f"Филиал в городе {city_of(row)} — {head_title}"
    else:
        title = f"{label} — филиал: {head_title}" if head_title else label
    items.append({"id": vid, "name": title, "city": city_of(row),
                  "region": row["region"], "mid": row["mid"], **({"parent": parent} if parent else {})})

items.sort(key=lambda v: (v["city"], v["name"]))
out = {"year": raw["year"], "source": "https://monitoring.miccedu.ru/?m=vpo", "items": items,
       "known": sorted(matched.values(), key=lambda v: v["id"])}
(src / "vuzdir.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print("новых вузов:", len(heads), "филиалов:", len(items) - len(heads), "уже были в приложении:", len(matched),
      "филиалов без головного вуза:", lost)
