"""Общая нормализация названий олимпиад: по ней олимпиада узнаётся и в перечне следующего года,
где у неё может быть другой номер. Та же функция есть в src/data/index.ts (normName)."""
import re


def norm_name(name):
    s = name.lower().replace("ё", "е")
    s = re.sub(r"[^0-9a-zа-я ]+", " ", s)
    s = re.sub(r"\b[ivxlc]+\b", " ", s)  # «XIX Южно-Российская…» → без номера года
    return re.sub(r"\s+", " ", s).strip()


def match(name, known):
    """known: {ключ: нормализованное название}. Возвращает ключ самой похожей олимпиады или None."""
    n = norm_name(name)
    for k, v in known.items():
        if v == n:
            return k
    words = set(n.split())
    best, score = None, 0.0
    for k, v in known.items():
        other = set(v.split())
        j = len(words & other) / max(len(words | other), 1)
        if j > score:
            best, score = k, j
    return best if score >= 0.8 else None
