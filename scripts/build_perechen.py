"""Turns the table scraped from rsr-olymp.ru into src/data/perechen.json.

Usage: python scripts/build_perechen.py
"""
import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit


def ascii_url(url):
    """https://мош.цпм.рф → https://xn--l1ae4a.xn--l1afu.xn--p1ai (так ссылку откроет любой браузер)."""
    url = url.strip()
    if not url:
        return url
    parts = urlsplit(url)
    try:
        host = parts.hostname.encode("idna").decode() if parts.hostname else parts.netloc
    except UnicodeError:
        return url
    return urlunsplit((parts.scheme, host, parts.path, parts.query, parts.fragment))

root = Path(__file__).resolve().parent.parent
rows = json.loads((root / "scripts" / "rsosh_rows.json").read_text(encoding="utf-8"))

olympiads = {}
current = None
for row in rows:
    c = row["c"]
    if len(c) == 5:  # first row of an olympiad: number, name, profile, subjects, level
        num = int(c[0])
        url = ascii_url(row["l"][0]) if row["l"] else ""
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
