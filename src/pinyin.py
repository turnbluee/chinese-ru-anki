"""Normalization and strict validation for numbered-tone pinyin."""

from __future__ import annotations

import re
import unicodedata

TONE_MARKED = frozenset(
    "āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ"
    "ĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙǕǗǙǛ"
)
_CURLY_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'", "＇": "'"})
_VALID_PINYIN = re.compile(r"[a-zv]+[0-4](?:[a-zv]*[0-4])*(?:'[a-zv]+[0-4](?:[a-zv]*[0-4])*)*")


def contains_tone_marks(value: str) -> bool:
    """Return True for precomposed or combining pinyin tone marks."""
    if any(char in TONE_MARKED for char in value):
        return True
    decomposed = unicodedata.normalize("NFD", value)
    return any(char in "\u0304\u0301\u030c\u0300" for char in decomposed)


def normalize_pinyin(value: str) -> str:
    """Normalize accepted user spelling without inventing tone numbers."""
    return "".join(value.strip().lower().translate(_CURLY_APOSTROPHES).replace("ü", "v").split())


def validate_stored_pinyin(value: str) -> str | None:
    """Return a human-readable error, or None for valid stored pinyin."""
    if not value:
        return "Pinyin пуст"
    if contains_tone_marks(value):
        return "Pinyin содержит диакритические знаки тона; используйте номера 0–4"
    if "5" in value:
        return "Pinyin содержит запрещённый тон 5; нейтральный тон всегда обозначается 0"
    if value != value.lower():
        return "Pinyin должен храниться в lowercase"
    normalized = normalize_pinyin(value)
    if normalized != value:
        return "Pinyin должен храниться без пробелов и с ASCII-апострофом"
    if not _VALID_PINYIN.fullmatch(normalized):
        return "каждый слог Pinyin должен оканчиваться номером тона 0–4"
    return None


def pinyin_matches(user_value: str, expected: str) -> tuple[bool, str | None]:
    """Compare user input and return a specific format error when useful."""
    if contains_tone_marks(user_value):
        return False, "Требуется pinyin с номерами тонов, без диакритики."
    normalized = normalize_pinyin(user_value)
    if "5" in normalized:
        return False, "Тон 5 запрещён: нейтральный тон обозначается 0."
    if not _VALID_PINYIN.fullmatch(normalized):
        return False, "Каждый слог должен содержать номер тона 0–4."
    return normalized == normalize_pinyin(expected), None
