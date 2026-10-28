"""Generate the offline Chinese → Russian Anki package."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import genanki

from build_assets import build_assets
from validators import CardRecord, ValidationError, read_cards

ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = 1729041801
DECK_ID = 1729041802
# Shown on the back of every card; tag GitHub releases as v<DECK_VERSION>.
DECK_VERSION = "1.0.0"


def read_template(name: str) -> str:
    return (ROOT / "templates" / name).read_text(encoding="utf-8")


def media_names(media: list[Path]) -> dict[str, str]:
    """Map template media names like _card.js to their hashed build names."""
    return {re.sub(r"-[0-9a-f]{10}(?=\.)", "", path.name, count=1): path.name for path in media}


def create_model(media: list[Path] | None = None) -> genanki.Model:
    names = media_names(media or [])

    def template(name: str) -> str:
        text = read_template(name)
        for plain, hashed in names.items():
            text = text.replace(f'src="{plain}"', f'src="{hashed}"')
        return text.replace("__DECK_VERSION__", DECK_VERSION)

    return genanki.Model(
        MODEL_ID,
        "Chinese RU Handwriting",
        fields=[{"name": name} for name in ("UID", "Hanzi", "Pinyin", "Russian", "RussianAccepted", "Notes")],
        templates=[
            {
                "name": "Russian → Chinese",
                "qfmt": template("ru_to_zh_front.html"),
                "afmt": template("ru_to_zh_back.html"),
            },
            {
                "name": "Chinese → Russian",
                "qfmt": template("zh_to_ru_front.html"),
                "afmt": template("zh_to_ru_back.html"),
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
    asset_records: list[CardRecord] | None = None,
) -> Path:
    """Build a package; asset_records defaults to the package's own records.

    All packages share one note type, so packages that may be imported into the
    same collection must embed handwriting data for every character they share.
    """
    records = [record for deck_records, _, _ in deck_specs for record in deck_records]
    if not records:
        raise ValidationError("Нельзя собрать пакет без записей")
    uids = [record.uid for record in records]
    if len(uids) != len(set(uids)):
        raise ValidationError("Одна запись попала в несколько наборов одного пакета")
    media = build_assets(asset_records or records, card_script=ROOT / "web" / "card.js")
    model = create_model(media)
    decks = [create_deck(deck_records, deck_id, deck_name, model) for deck_records, deck_id, deck_name in deck_specs]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    genanki.Package(decks, media_files=[str(path) for path in media]).write_to_file(str(output_path))
    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError(f"Сборка не создала непустой файл {output_path}")
    return output_path


def build_deck(input_path: Path, output_path: Path) -> Path:
    records = read_cards(input_path)
    return build_package([(records, DECK_ID, "Китайский МФТИ A1")], output_path)


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
