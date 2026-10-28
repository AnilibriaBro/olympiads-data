"""Календари со сроками олимпиад: data/ics/<id>.ics, по одному на олимпиаду.

На iPhone приложение подписывает на такой календарь (webcal://), и Календарь сам
перечитывает файл раз в день — если организаторы перенесут даты, они обновятся и в телефоне.
Только настоящие даты с olimpiada.ru: ориентировочные в календарь не попадают.

Usage: python scripts/build_ics.py   (запускается из update_all.py)
"""
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
scripts = Path(__file__).resolve().parent
sys.path.insert(0, str(scripts))
from names import match  # noqa: E402

project = scripts.parent
src = project / "src" / "data"
out = project / "data" / "ics"


def esc(text):
    return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def fold(line):
    """Строки .ics не длиннее 75 байт: длинные переносятся с пробелом в начале."""
    raw = line.encode("utf-8")
    if len(raw) <= 75:
        return line
    parts, cur = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        if len(cur) + len(b) > (75 if not parts else 74):
            parts.append(cur.decode("utf-8"))
            cur = b""
        cur += b
    parts.append(cur.decode("utf-8"))
    return "\r\n ".join(parts)


def short(name):
    m = re.search(r"«(.+?)»", name)
    return m.group(1) if m else (name if len(name) <= 60 else name[:57] + "…")


def day(iso):
    return date.fromisoformat(iso).strftime("%Y%m%d")


def next_day(iso):
    return (date.fromisoformat(iso) + timedelta(days=1)).strftime("%Y%m%d")


def event(uid, summary, start, end, url, alarm, alarm_text):
    return [
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{STAMP}",
        f"DTSTART;VALUE=DATE:{day(start)}",
        f"DTEND;VALUE=DATE:{next_day(end)}",
        f"SUMMARY:{esc(summary)}",
        f"URL:{url}",
        f"DESCRIPTION:{esc('Сайт олимпиады: ' + url)}",
        "TRANSP:TRANSPARENT",
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        f"DESCRIPTION:{esc(alarm_text)}",
        f"TRIGGER:{alarm}",
        "END:VALARM",
        "END:VEVENT",
    ]


# Постоянная отметка времени: файлы меняются только когда меняются даты, а не каждый день
_season = (scripts / "rsosh_season.txt")
STAMP = (f"{_season.read_text(encoding='utf-8')[:4]}0801T000000Z" if _season.exists()
         else datetime.now(timezone.utc).strftime("%Y0801T000000Z"))


def main():
    known = json.loads((src / "names.json").read_text(encoding="utf-8"))
    perechen = json.loads((src / "perechen.json").read_text(encoding="utf-8"))
    dates = json.loads((src / "dates.json").read_text(encoding="utf-8"))
    out.mkdir(parents=True, exist_ok=True)
    written = set()
    for o in perechen:
        stages = (dates.get(str(o["num"])) or {}).get("stages") or []
        if not stages:
            continue
        frozen = match(o["name"], known)
        oid = int(frozen) if frozen else 1000 + o["num"]  # тот же номер, что у олимпиады в приложении
        title = short(o["name"])
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Olympiads app//RU",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
            f"X-WR-CALNAME:{esc('Олимпиада: ' + title)}",
            "X-WR-TIMEZONE:Europe/Moscow",
            "REFRESH-INTERVAL;VALUE=DURATION:P1D",
            "X-PUBLISHED-TTL:P1D",
        ]
        for i, st in enumerate(stages):
            uid = f"olymp-{oid}-{i}@anilibriabro.github.io"
            # Событие на весь день начинается в 00:00, значит −14 часов — это 10:00 накануне
            lines += event(uid, f"{title}: {st['name'].lower()}", st["start"], st["end"], o["url"],
                           "-PT14H", f"Завтра: {st['name'].lower()} — {title}")
            if "регистрац" in st["name"].lower() and st["start"] != st["end"]:
                lines += event(f"olymp-{oid}-{i}-close@anilibriabro.github.io", f"{title}: последний день регистрации",
                               st["end"], st["end"], o["url"], "-P1DT14H",
                               f"Через два дня закрывается регистрация — {title}")
        lines.append("END:VCALENDAR")
        (out / f"{oid}.ics").write_bytes(("\r\n".join(fold(l) for l in lines) + "\r\n").encode("utf-8"))
        written.add(f"{oid}.ics")
    # Календари олимпиад, у которых больше нет дат, удаляем
    for f in out.glob("*.ics"):
        if f.name not in written:
            f.unlink()
    print("calendars:", len(written))


if __name__ == "__main__":
    main()
