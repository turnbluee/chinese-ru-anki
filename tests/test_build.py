import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

from build_assets import build_assets
from build_deck import create_model, stable_guid
from build_lessons import RADICAL_LESSONS, build_lesson_packages, split_by_lesson
from validators import CardRecord, ValidationError


def fake_record(hanzi: str, line: int = 2) -> CardRecord:
    return CardRecord("uid", hanzi, "ni3", "тест", "тест", "", line)


def test_stable_genanki_guid():
    assert stable_guid("zhidao-001") == stable_guid("zhidao-001")
    assert stable_guid("zhidao-001") != stable_guid("ni-001")


def test_model_has_exactly_two_card_types():
    model = create_model()
    assert model.model_id == 1729041801
    assert model.name == "Chinese RU Handwriting"
    assert len(model.templates) == 2
    assert [item["name"] for item in model.templates] == ["Russian → Chinese", "Chinese → Russian"]


def test_stable_deck_id():
    from build_deck import DECK_ID

    assert DECK_ID == 1729041802


def test_lesson_and_radical_deck_ids_are_stable_and_unique():
    from build_lessons import LESSONS

    ids = [deck_id for deck_id, _ in LESSONS.values()]
    radical_ids = [deck_id for deck_id, _ in RADICAL_LESSONS.values()]
    assert ids == [1729041803, 1729041804, 1729041805, 1729041806]
    assert radical_ids == [1729041811, 1729041812, 1729041813, 1729041814]
    assert len(set(ids + radical_ids)) == 8


def test_records_are_split_between_lessons():
    from build_deck import ROOT
    from validators import read_cards

    lessons = split_by_lesson(read_cards(ROOT / "data" / "cards.tsv"))
    assert {number: len(records) for number, records in lessons.items()} == {
        1: 12,
        2: 43,
        3: 51,
        4: 72,
    }
    assert not ({record.uid for record in lessons[1]} & {record.uid for record in lessons[2]})


def test_radicals_match_the_four_textbook_exercises():
    from build_deck import ROOT
    from validators import read_cards

    lessons = split_by_lesson(
        read_cards(ROOT / "data" / "radicals.tsv"), RADICAL_LESSONS
    )
    assert {number: len(records) for number, records in lessons.items()} == {
        1: 9,
        2: 28,
        3: 22,
        4: 35,
    }
    assert sum(len(records) for records in lessons.values()) == 94


def test_asset_generation_contains_only_requested_hanzi(tmp_path: Path):
    data_package = tmp_path / "data-package"
    output = tmp_path / "generated"
    data_package.mkdir()
    for char in "你好没":
        (data_package / f"{char}.json").write_text(json.dumps({"character": char}), encoding="utf-8")
    writer = tmp_path / "writer.js"
    writer.write_text("window.HanziWriter = {};", encoding="utf-8")
    card = tmp_path / "card.js"
    card.write_text("window.ChineseCards = {};", encoding="utf-8")

    outputs = build_assets([fake_record("你 A好!")], output, data_package, writer, card)
    generated = (output / "_hanzi-data.js").read_text(encoding="utf-8")
    assert '"你"' in generated and '"好"' in generated
    assert '"没"' not in generated
    assert all(path.name.startswith("_") for path in outputs)
    assert not any(path.is_symlink() for path in outputs)


def test_missing_hanzi_data_has_useful_error(tmp_path: Path):
    writer = tmp_path / "writer.js"
    writer.write_text("writer", encoding="utf-8")
    with pytest.raises(ValidationError, match=r"Строка 17.*Hanzi.*龘.*отсутствует"):
        build_assets([fake_record("龘", 17)], tmp_path / "out", tmp_path / "data", writer)


def test_real_deck_build_exists_and_is_nonempty(tmp_path: Path):
    pytest.importorskip("genanki")
    from build_deck import ROOT, build_deck

    output = tmp_path / "chinese-ru.apkg"
    build_deck(ROOT / "data" / "cards.tsv", output)
    assert output.is_file()
    assert output.stat().st_size > 1000


def test_all_lesson_and_radical_packages_are_built(tmp_path: Path):
    from build_deck import ROOT

    outputs = build_lesson_packages(
        ROOT / "data" / "cards.tsv",
        ROOT / "data" / "radicals.tsv",
        tmp_path,
    )
    assert {path.name for path in outputs} == {
        "chinese-ru-lesson-01.apkg",
        "chinese-ru-lesson-02.apkg",
        "chinese-ru-lesson-03.apkg",
        "chinese-ru-lesson-04.apkg",
        "chinese-ru.apkg",
        "chinese-ru-radicals-lesson-01.apkg",
        "chinese-ru-radicals-lesson-02.apkg",
        "chinese-ru-radicals-lesson-03.apkg",
        "chinese-ru-radicals-lesson-04.apkg",
    }
    assert all(path.stat().st_size > 1000 for path in outputs)

    with zipfile.ZipFile(tmp_path / "chinese-ru.apkg") as package:
        collection = tmp_path / "collection.anki2"
        collection.write_bytes(package.read("collection.anki2"))
    with sqlite3.connect(collection) as db:
        decks = json.loads(db.execute("select decks from col").fetchone()[0])
        used = {did for (did,) in db.execute("select distinct did from cards")}
    from build_lessons import LESSONS

    expected = {deck_id: name for deck_id, name in [*LESSONS.values(), *RADICAL_LESSONS.values()]}
    assert {did: decks[str(did)]["name"] for did in used} == expected
