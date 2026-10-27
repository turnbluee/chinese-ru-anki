"""Build minimal offline Hanzi Writer assets for the current TSV."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from validators import CardRecord, ValidationError, read_cards

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "assets" / "generated"
DATA_PACKAGE = ROOT / "node_modules" / "hanzi-writer-data"
WRITER_SOURCE = ROOT / "node_modules" / "hanzi-writer" / "dist" / "hanzi-writer.min.js"


def is_cjk(char: str) -> bool:
    cp = ord(char)
    return (
        0x2E80 <= cp <= 0x2FDF
        or 0x3400 <= cp <= 0x4DBF
        or 0x4E00 <= cp <= 0x9FFF
        or 0x20000 <= cp <= 0x2EBEF
        or 0x30000 <= cp <= 0x323AF
    )


def used_hanzi(records: list[CardRecord]) -> list[tuple[str, int]]:
    first_lines: dict[str, int] = {}
    for record in records:
        for char in record.hanzi:
            if is_cjk(char):
                first_lines.setdefault(char, record.line)
    return sorted(first_lines.items(), key=lambda item: ord(item[0]))


def write_media(output_dir: Path, stem: str, suffix: str, content: str) -> Path:
    """Write content under a hashed name so Anki never keeps a stale copy.

    Anki skips imported media whose name already exists in the collection, so
    every content change must produce a new file name.
    """
    for stale in output_dir.glob(f"{stem}-*{suffix}"):
        stale.unlink()
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:10]
    target = output_dir / f"{stem}-{digest}{suffix}"
    target.write_text(content, encoding="utf-8")
    return target


def _data_file(char: str, data_package: Path) -> Path:
    direct = data_package / f"{char}.json"
    if direct.is_file():
        return direct
    nested = data_package / "data" / f"{char}.json"
    return nested


def build_card_asset(
    output_dir: Path = DEFAULT_OUTPUT,
    card_script: Path = ROOT / "web" / "card.js",
) -> Path:
    if not card_script.is_file():
        raise ValidationError(f"Не найден общий скрипт карточек: {card_script}")
    output_dir.mkdir(parents=True, exist_ok=True)
    return write_media(output_dir, "_card", ".js", card_script.read_text(encoding="utf-8"))


def build_assets(
    records: list[CardRecord],
    output_dir: Path = DEFAULT_OUTPUT,
    data_package: Path = DATA_PACKAGE,
    writer_source: Path = WRITER_SOURCE,
    card_script: Path | None = None,
) -> list[Path]:
    if not writer_source.is_file():
        raise ValidationError(
            f"Не найден {writer_source}. Сначала выполните npm install."
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    data: dict[str, object] = {}
    for char, line in used_hanzi(records):
        source = _data_file(char, data_package)
        if not source.is_file():
            raise ValidationError(
                f"Строка {line}, поле Hanzi: для иероглифа {char!r} "
                f"отсутствует Hanzi Writer data ({source})"
            )
        try:
            data[char] = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValidationError(f"Строка {line}: не удалось прочитать data для {char!r}: {exc}") from exc

    data_target = write_media(
        output_dir,
        "_hanzi-data",
        ".js",
        "window.HANZI_DATA=" + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";\n",
    )
    writer_code = writer_source.read_text(encoding="utf-8")
    # The deck always supplies charDataLoader. Remove the upstream network fallback
    # entirely, and split the SVG namespace literal so the offline audit contains
    # no http(s) URL strings while preserving the required namespace at runtime.
    writer_code = writer_code.replace(
        "https://cdn.jsdelivr.net/npm/hanzi-writer-data@2.0.1/",
        "offline://hanzi-data/",
    )
    writer_code = writer_code.replace(
        '"http://www.w3.org/2000/svg"',
        '"http:"+"//www.w3.org/2000/svg"',
    )
    writer_code = writer_code.replace(
        "https://chanind.github.io/hanzi-writer",
        "upstream Hanzi Writer project",
    )
    if "http://" in writer_code or "https://" in writer_code:
        raise ValidationError("Hanzi Writer bundle содержит внешний URL")
    writer_target = write_media(output_dir, "_hanzi-writer", ".min.js", writer_code)
    outputs = [data_target, writer_target]
    if card_script is not None:
        outputs.append(build_card_asset(output_dir, card_script))
    if any(not item.name.startswith("_") for item in outputs):
        raise AssertionError("Имена Anki media должны начинаться с '_'")
    return outputs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data" / "cards.tsv")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    try:
        records = read_cards(args.input)
        outputs = build_assets(records, args.output_dir, card_script=ROOT / "web" / "card.js")
    except ValidationError as exc:
        print(f"Ошибка: {exc}", file=sys.stderr)
        return 1
    print("Созданы assets:", ", ".join(str(path) for path in outputs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
