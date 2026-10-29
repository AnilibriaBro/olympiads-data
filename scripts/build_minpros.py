"""Перечень олимпиад и конкурсов Минпросвещения (приказ № 598 от 28.08.2026, на 2026/27 год)
-> src/data/minpros.json. Из этого перечня вузы выбирают, за что давать доп. баллы при поступлении.

Берём направления «Наука и образование» и «Искусство и культура» (без спорта) и без ВсОШ — она в приложении отдельно.
Usage:
  python scripts/build_minpros.py <страница приказа на garant.ru, сохранённая как .html>   — разобрать заново
  python scripts/build_minpros.py                                                      — из scripts/minpros_rows.json
Перечень утверждают раз в год (обычно в августе–сентябре): тогда сохраните новую страницу и запустите с ней.
"""
import html
import json
import re
import sys
import zlib
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
scripts = Path(__file__).resolve().parent
sys.path.insert(0, str(scripts))
from names import norm_name  # noqa: E402
from minpros_vuzes import vuz_of  # noqa: E402

ORDER = "№ 598 от 28.08.2026"
SOURCE = "https://www.garant.ru/products/ipo/prime/doc/414884344/"
LEVELS = ["Высший уровень", "I уровень", "II уровень", "III уровень", "IV уровень"]


def clean(s):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s))).strip()


def parse_html(path):
    s = Path(path).read_bytes().decode("cp1251", errors="replace")
    table = max(re.findall(r"<table.*?</table>", s, re.S), key=len)
    return [[clean(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
            for tr in re.findall(r"<tr.*?</tr>", table, re.S)]


def short_org(org):
    """«Федеральное государственное … высшего образования “Томский политехнический университет”» → «Томский политехнический университет»."""
    m = re.search(r"[“«\"](.{4,})[”»\"]", org)  # от первой открывающей до последней закрывающей кавычки
    if m and re.search(r"учреждение|организация|общество|фонд|центр|ассоциация", org, re.I):
        name = m.group(1).strip()
        # «Университет “Высшая школа экономики» — дописываем закрывающую кавычку для вложенных
        name += "”" * (name.count("“") - name.count("”")) + "»" * (name.count("«") - name.count("»"))
        return name
    return org


# Вуз — это организация «высшего образования» или университет; «Малая академия наук» и институты развития образования — нет
VUZ = re.compile(r"высшего образования|университет|консерватори", re.I)


def build(rows):
    items, cur = [], None
    for r in rows:
        if len(r) == 6 and re.match(r"^\d+(\.\d+)+$", r[0]):
            cur = {"n": r[0], "name": r[1], "org": r[2], "parts": [(r[3], r[4], r[5])]}
            items.append(cur)
        elif len(r) == 3 and cur is not None:
            cur["parts"].append((r[0], r[1], r[2]))  # следующий профиль того же мероприятия
    out = []
    for it in items:
        if it["n"].startswith("1."):
            continue  # ВсОШ
        sci = [p for p in it["parts"] if p[0].startswith("Наука")]
        art = [p for p in it["parts"] if p[0].startswith("Искусство")]
        kind = "science" if sci else "art"
        sci = sci or art  # спорт и «иное» не берём
        if not sci:
            continue
        levels = [p[2].rstrip(".") for p in sci]
        known = [lv for lv in levels if lv in LEVELS]
        best = min(known, key=LEVELS.index) if known else "Не установлен"
        profiles = []
        for p in sci:
            for x in re.split(r"[;,]\s*", p[1]):
                x = x.strip()
                if x and x not in profiles:
                    profiles.append(x)
        vz = vuz_of(it["org"]) if VUZ.search(it["org"]) else None
        out.append({
            # Постоянный номер по названию: чтобы отметки в «Моих олимпиадах» не съехали, когда номер в перечне поменяется
            "id": 1_000_000 + zlib.crc32((norm_name(it["name"]) + "|" + norm_name(it["org"])).encode("utf-8")) % 900_000_000,
            "n": it["n"],
            "name": it["name"],
            "org": short_org(it["org"]),
            "profile": "; ".join(profiles),
            "level": best,
            "vuz": vz is not None,
            "vuzId": vz[0] if vz else "",
            "_vuz": vz,
            "intl": it["n"].startswith("3."),
            "kind": kind,
        })
    return out


def main():
    rows_file = scripts / "minpros_rows.json"
    if len(sys.argv) > 1:
        rows = parse_html(sys.argv[1])
        rows_file.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    else:
        rows = json.loads(rows_file.read_text(encoding="utf-8"))
    items = build(rows)
    # Два тура одной олимпиады в одном году («XXI …» и «XXII …») различаем по полному названию с номером
    seen = {}
    for i in items:
        seen.setdefault(i["id"], []).append(i)
    for same in seen.values():
        if len(same) > 1:
            for i in same:
                i["id"] = 1_000_000 + zlib.crc32((i["name"] + "|" + i["org"]).encode("utf-8")) % 900_000_000
    ids = [i["id"] for i in items]
    if len(set(ids)) != len(ids):
        dup = [i["name"] for i in items if ids.count(i["id"]) > 1]
        raise SystemExit(f"Совпали номера у разных мероприятий: {dup[:4]}")
    if len(items) < 300:
        raise SystemExit(f"Подозрительно мало мероприятий ({len(items)}) — таблица могла измениться")
    # Та же олимпиада уже есть в приложении: в перечне РСОШ (даёт БВИ) или в «Баллах в вузах».
    # Такие записи помечаем полем same — в списке перечня Минпроса они не показываются второй раз.
    from names import match
    data_dir = scripts.parent / "src" / "data"
    known = json.loads((data_dir / "names.json").read_text(encoding="utf-8"))
    rsosh = {norm_name(o["name"]): o for o in json.loads((data_dir / "perechen.json").read_text(encoding="utf-8"))}
    extra = json.loads((scripts / "extra_olympiads.json").read_text(encoding="utf-8"))["items"]
    by_name = {e["minpros"]: e["id"] for e in extra if e.get("minpros")}
    for i in items:
        o = rsosh.get(norm_name(i["name"]))
        if o:
            frozen = match(o["name"], known)
            i["same"] = {"rsosh": int(frozen) if frozen else 1000 + o["num"]}
        elif i["name"] in by_name:
            i["same"] = {"extra": by_name[i["name"]]}
    missing = set(by_name) - {i["name"] for i in items}
    if missing:
        raise SystemExit(f"В extra_olympiads.json указаны названия, которых нет в перечне: {sorted(missing)[:3]}")

    # Вузы, которых нет в src/data/vuzes.ts: название и город — для раздела «Вузы»
    vuzes = {}
    for i in items:
        vz = i.pop("_vuz")
        if vz and vz[2] is not None:
            vuzes.setdefault(vz[0], {"id": vz[0], "name": vz[1], "city": vz[2]})
    data = {"order": ORDER, "source": SOURCE, "items": items,
            "vuzes": sorted(vuzes.values(), key=lambda v: v["name"])}
    (scripts.parent / "src" / "data" / "minpros.json").write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("мероприятий:", len(items), "из них проводят вузы:", sum(i["vuz"] for i in items),
          "вузов-организаторов:", len({i["vuzId"] for i in items if i["vuzId"]}), "новых вузов:", len(vuzes),
          "без города:", sum(1 for v in vuzes.values() if not v["city"]),
          "международных:", sum(i["intl"] for i in items), "творческих:", sum(i["kind"] == "art" for i in items),
          "уже есть в приложении:", sum(1 for i in items if i.get("same")))


if __name__ == "__main__":
    main()
