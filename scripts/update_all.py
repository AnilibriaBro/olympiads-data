"""Полное обновление данных: перечень, даты, сводный файл для приложения.

Usage: python scripts/update_all.py
Результат:
  src/data/*.json  — данные, которые попадают внутрь APK;
  data/data.json   — тот же набор одним файлом, его приложение скачивает при запуске.
Запускается каждый день на GitHub (.github/workflows/update-data.yml).
"""
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
scripts = Path(__file__).resolve().parent
project = scripts.parent

for step in ["fetch_perechen.py", "build_perechen.py", "fetch_dates.py", "build_dates.py", "build_ics.py",
             "build_minpros.py"]:
    print("==>", step, flush=True)
    subprocess.run([sys.executable, "-I", str(scripts / step)], check=True)

src = project / "src" / "data"
# Список олимпиад вне перечня ведётся вручную (scripts/extra_olympiads.json); комментарий в приложение не нужен
extra = json.loads((scripts / "extra_olympiads.json").read_text(encoding="utf-8"))
extra.pop("_comment", None)
(src / "extra.json").write_text(json.dumps(extra, ensure_ascii=False, indent=1), encoding="utf-8")
data = {
    "version": 1,
    "season": (scripts / "rsosh_season.txt").read_text(encoding="utf-8").strip(),
    "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    "perechen": json.loads((src / "perechen.json").read_text(encoding="utf-8")),
    "dates": json.loads((src / "dates.json").read_text(encoding="utf-8")),
    "extra": extra,
    "minpros": json.loads((src / "minpros.json").read_text(encoding="utf-8")),
}
out = project / "data"
out.mkdir(exist_ok=True)
(out / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
(src / "updated.json").write_text(json.dumps({"updated": data["updated"], "season": data["season"]}), encoding="utf-8")
print("data/data.json:", round((out / "data.json").stat().st_size / 1024), "KB, updated", data["updated"])
