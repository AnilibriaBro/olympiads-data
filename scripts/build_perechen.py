"""Turns the table scraped from rsr-olymp.ru into src/data/perechen.json.

Usage: python scripts/build_perechen.py
"""
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
rows = json.loads((root / "scripts" / "rsosh_rows.json").read_text(encoding="utf-8"))

olympiads = {}
current = None
for row in rows:
    c = row["c"]
    if len(c) == 5:  # first row of an olympiad: number, name, profile, subjects, level
        num = int(c[0])
        url = row["l"][0].strip() if row["l"] else ""
        if num not in olympiads:
            olympiads[num] = {"num": num, "name": c[1], "url": url, "profiles": []}
        current = olympiads[num]
        profile = c[2:]
        profile_url = url
    else:
        profile = c
        profile_url = ""
    name, subjects, level = profile
    entry = {"profile": name, "subjects": subjects, "level": int(level)}
    if profile_url and profile_url != current["url"]:
        entry["url"] = profile_url
    current["profiles"].append(entry)

out = sorted(olympiads.values(), key=lambda o: o["num"])
(root / "src" / "data" / "perechen.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print(len(out), "olympiads,", sum(len(o["profiles"]) for o in out), "profiles")
