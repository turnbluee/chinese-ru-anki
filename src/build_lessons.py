"""Build per-lesson packages and one combined package with word and radical subdecks."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from build_deck import ROOT, build_package
from validators import CardRecord, ValidationError, read_cards

LESSONS = {
    1: (1729041803, "Китайский МФТИ A1::Слова::Урок 1"),
    2: (1729041804, "Китайский МФТИ A1::Слова::Урок 2"),
    3: (1729041805, "Китайский МФТИ A1::Слова::Урок 3"),
    4: (1729041806, "Китайский МФТИ A1::Слова::Урок 4"),
    5: (1729041807, "Китайский МФТИ A1::Слова::Урок 5"),
    6: (1729041808, "Китайский МФТИ A1::Слова::Урок 6"),
}

RADICAL_LESSONS = {
    1: (1729041811, "Китайский МФТИ A1::Ключи::Урок 1"),
    2: (1729041812, "Китайский МФТИ A1::Ключи::Урок 2"),
    3: (1729041813, "Китайский МФТИ A1::Ключи::Урок 3"),
    4: (1729041814, "Китайский МФТИ A1::Ключи::Урок 4"),
    5: (1729041815, "Китайский МФТИ A1::Ключи::Урок 5"),
    6: (1729041816, "Китайский МФТИ A1::Ключи::Урок 6"),
}


def split_by_lesson(
    records: list[CardRecord],
    lesson_specs: dict[int, tuple[int, str]] = LESSONS,
) -> dict[int, list[CardRecord]]:
    result = {number: [] for number in lesson_specs}
    for record in records:
        matches = [
            number
            for number in lesson_specs
            if re.search(rf"(?:^|;\s*)Урок {number}(?:;|$)", record.notes)
        ]
        if len(matches) != 1:
            expected = ", ".join(f"'Урок {number}'" for number in lesson_specs)
            raise ValidationError(
                f"Строка {record.line}: запись {record.uid!r} должна содержать ровно одну пометку "
                f"из {expected} в Notes"
            )
        result[matches[0]].append(record)
    return result


def build_lesson_packages(
    input_path: Path,
    radicals_path: Path,
    output_dir: Path,
) -> list[Path]:
    words = read_cards(input_path)
    radical_records = read_cards(radicals_path)
    lessons = split_by_lesson(words)
    radicals = split_by_lesson(radical_records, RADICAL_LESSONS)
    all_records = words + radical_records
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    for number, (deck_id, deck_name) in LESSONS.items():
        output = output_dir / f"chinese-ru-lesson-{number:02d}.apkg"
        outputs.append(build_package([(lessons[number], deck_id, deck_name)], output, all_records))

    for number, (deck_id, deck_name) in RADICAL_LESSONS.items():
        output = output_dir / f"chinese-ru-radicals-lesson-{number:02d}.apkg"
        outputs.append(build_package([(radicals[number], deck_id, deck_name)], output, all_records))

    combined_specs = [
        (lessons[number], deck_id, deck_name)
        for number, (deck_id, deck_name) in LESSONS.items()
    ] + [
        (radicals[number], deck_id, deck_name)
        for number, (deck_id, deck_name) in RADICAL_LESSONS.items()
    ]
    outputs.append(build_package(combined_specs, output_dir / "chinese-ru.apkg", all_records))
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data" / "cards.tsv")
    parser.add_argument("--radicals", type=Path, default=ROOT / "data" / "radicals.tsv")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "dist")
    args = parser.parse_args(argv)
    try:
        outputs = build_lesson_packages(args.input, args.radicals, args.output_dir)
    except (ValidationError, OSError, RuntimeError) as exc:
        print(f"Ошибка сборки: {exc}", file=sys.stderr)
        return 1
    for output in outputs:
        print(f"Колода создана: {output} ({output.stat().st_size} байт)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
