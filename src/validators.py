"""Input validation for the deck TSV."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from pinyin import validate_stored_pinyin

REQUIRED_COLUMNS = ("uid", "hanzi", "pinyin", "russian", "russian_accepted", "notes")


@dataclass(frozen=True)
class CardRecord:
    uid: str
    hanzi: str
    pinyin: str
    russian: str
    russian_accepted: str
    notes: str
    line: int


class ValidationError(ValueError):
    pass


def normalize_russian(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower().replace("ё", "е"))


def russian_matches(value: str, accepted: str) -> bool:
    actual = normalize_russian(value)
    return any(actual == normalize_russian(option) for option in accepted.split("|"))


def read_cards(path: str | Path) -> list[CardRecord]:
    path = Path(path)
    try:
        handle = path.open("r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise ValidationError(f"Не удалось открыть TSV {path}: {exc}") from exc

    with handle:
        reader = csv.DictReader(handle, delimiter="\t")
        if reader.fieldnames != list(REQUIRED_COLUMNS):
            raise ValidationError(
                "Строка 1: ожидаются колонки в точном порядке: " + "\t".join(REQUIRED_COLUMNS)
            )
        records: list[CardRecord] = []
        seen: dict[str, int] = {}
        for line, row in enumerate(reader, start=2):
            if None in row:
                raise ValidationError(f"Строка {line}: лишние TSV-колонки")
            uid = row["uid"].strip()
            hanzi = row["hanzi"].strip()
            pinyin = row["pinyin"].strip()
            russian = row["russian"].strip()
            accepted = row["russian_accepted"].strip()
            notes = row["notes"].strip()
            errors: list[str] = []
            if not uid:
                errors.append("UID пуст")
            elif uid in seen:
                errors.append(f"UID {uid!r} дублируется (первая запись: строка {seen[uid]})")
            if not hanzi:
                errors.append("Hanzi пуст")
            if not russian:
                errors.append("Russian пуст")
            pinyin_error = validate_stored_pinyin(pinyin)
            if pinyin_error:
                errors.append(pinyin_error)
            if not accepted:
                errors.append("RussianAccepted пуст")
            elif any(not normalize_russian(item) for item in accepted.split("|")):
                errors.append("RussianAccepted содержит пустой вариант")
            if errors:
                raise ValidationError(f"Строка {line}: " + "; ".join(errors))
            seen[uid] = line
            records.append(CardRecord(uid, hanzi, pinyin, russian, accepted, notes, line))
    if not records:
        raise ValidationError("TSV не содержит записей (после строки 1)")
    return records

