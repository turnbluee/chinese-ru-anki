"""Generate the offline Chinese → Russian Anki package."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import genanki

from build_assets import build_assets
from validators import CardRecord, ValidationError, read_cards

ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = 1729041801
DECK_ID = 1729041802


def read_template(name: str) -> str:
    return (ROOT / "templates" / name).read_text(encoding="utf-8")


def create_model() -> genanki.Model:
    return genanki.Model(
        MODEL_ID,
        "Chinese RU Handwriting",
        fields=[{"name": name} for name in ("UID", "Hanzi", "Pinyin", "Russian", "RussianAccepted", "Notes")],
        templates=[
            {
                "name": "Russian → Chinese",
                "qfmt": read_template("ru_to_zh_front.html"),
                "afmt": read_template("ru_to_zh_back.html"),
            },
            {
                "name": "Chinese → Russian",
                "qfmt": read_template("zh_to_ru_front.html"),
                "afmt": read_template("zh_to_ru_back.html"),
            },
        ],
        css=read_template("style.css"),
        model_type=genanki.Model.FRONT_BACK,
    )


def stable_guid(uid: str) -> str:
    return genanki.guid_for("chinese-ru", uid)


def create_deck(records: list[CardRecord], deck_id: int, deck_name: str, model: genanki.Model) -> genanki.Deck:
    deck = genanki.Deck(deck_id, deck_name)
    for record in records:
        note = genanki.Note(
            model=model,
            fields=[record.uid, record.hanzi, record.pinyin, record.russian, record.russian_accepted, record.notes],
            guid=stable_guid(record.uid),
        )
        deck.add_note(note)
    return deck


def build_package(
    deck_specs: list[tuple[list[CardRecord], int, str]],
    output_path: Path,
) -> Path:
    records = [record for deck_records, _, _ in deck_specs for record in deck_records]
    if not records:
        raise ValidationError("Нельзя собрать пакет без записей")
    uids = [record.uid for record in records]
    if len(uids) != len(set(uids)):
        raise ValidationError("Одна запись попала в несколько наборов одного пакета")
    media = build_assets(records, card_script=ROOT / "web" / "card.js")
    model = create_model()
    decks = [create_deck(deck_records, deck_id, deck_name, model) for deck_records, deck_id, deck_name in deck_specs]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    genanki.Package(decks, media_files=[str(path) for path in media]).write_to_file(str(output_path))
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError(f"Сборка не создала непустой файл {output_path}")
    return output_path


def build_deck(input_path: Path, output_path: Path) -> Path:
    records = read_cards(input_path)
    return build_package([(records, DECK_ID, "Китайский для русскоязычных")], output_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = build_deck(args.input, args.output)
    except (ValidationError, OSError, RuntimeError) as exc:
        print(f"Ошибка сборки: {exc}", file=sys.stderr)
        return 1
    print(f"Колода создана: {result} ({result.stat().st_size} байт)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
