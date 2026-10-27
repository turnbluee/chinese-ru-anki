from pathlib import Path

import pytest

from validators import ValidationError, normalize_russian, read_cards, russian_matches


def test_russian_normalization():
    assert normalize_russian("  ЁЖИК   В ТУМАНЕ ") == "ежик в тумане"
    assert russian_matches(" КРАСИВАЯ ", "красивый|красивая|красиво")
    assert russian_matches("всё   хорошо", "все хорошо|ладно")
    assert not russian_matches("красив", "красивый|красивая")


def test_duplicate_uid_reports_tsv_line(tmp_path: Path):
    source = tmp_path / "cards.tsv"
    source.write_text(
        "uid\thanzi\tpinyin\trussian\trussian_accepted\tnotes\n"
        "same\t你\tni3\tты\tты\t\n"
        "same\t好\thao3\tхорошо\tхорошо\t\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match=r"Строка 3.*дублируется.*строка 2"):
        read_cards(source)


@pytest.mark.parametrize(
    ("pinyin", "fragment"),
    [("nǐ", "диакритические"), ("ni", "номером"), ("ma5", "тон 5")],
)
def test_invalid_pinyin_reports_line(tmp_path: Path, pinyin: str, fragment: str):
    source = tmp_path / "cards.tsv"
    source.write_text(
        "uid\thanzi\tpinyin\trussian\trussian_accepted\tnotes\n"
        f"one\t你\t{pinyin}\tты\tты\t\n",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match=rf"Строка 2.*{fragment}"):
        read_cards(source)


@pytest.mark.parametrize(
    ("row", "field"),
    [
        ("\t你\tni3\tты\tты\t\n", "UID"),
        ("one\t\tni3\tты\tты\t\n", "Hanzi"),
        ("one\t你\t\tты\tты\t\n", "Pinyin"),
        ("one\t你\tni3\t\tты\t\n", "Russian"),
    ],
)
def test_required_fields_report_line_and_name(tmp_path: Path, row: str, field: str):
    source = tmp_path / "cards.tsv"
    source.write_text(
        "uid\thanzi\tpinyin\trussian\trussian_accepted\tnotes\n" + row,
        encoding="utf-8",
    )
    with pytest.raises(ValidationError, match=rf"Строка 2.*{field}"):
        read_cards(source)
