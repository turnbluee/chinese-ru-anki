import json
import re
from pathlib import Path

from build_assets import ROOT, build_assets, is_cjk
from validators import read_cards


def test_real_assets_are_offline_minimal_and_anki_safe(tmp_path: Path):
    records = read_cards(ROOT / "data" / "cards.tsv")
    outputs = build_assets(
        records,
        output_dir=tmp_path,
        card_script=ROOT / "web" / "card.js",
    )
    names = {path.name for path in outputs}
    assert len(names) == 3
    assert all(re.fullmatch(r"_(hanzi-data|hanzi-writer|card)-[0-9a-f]{10}(\.min)?\.js", name) for name in names)

    generated = next(tmp_path.glob("_hanzi-data-*.js")).read_text(encoding="utf-8")
    used = {char for record in records for char in record.hanzi if is_cjk(char)}
    data = json.loads(generated.removeprefix("window.HANZI_DATA=").removesuffix(";\n"))
    assert set(data) == used
    all_media = "\n".join(path.read_text(encoding="utf-8") for path in outputs)
    assert "http://" not in all_media
    assert "https://" not in all_media


def test_cjk_radical_supplement_characters_are_handwriting_targets():
    assert is_cjk("⺮")
    assert is_cjk("⺌")


def test_templates_and_project_script_have_no_external_urls():
    paths = list((ROOT / "templates").glob("*")) + [ROOT / "web" / "card.js"]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    assert "http://" not in combined
    assert "https://" not in combined


def test_handwriting_feedback_is_deferred_until_check():
    script = (ROOT / "web" / "card.js").read_text(encoding="utf-8")
    front = (ROOT / "templates" / "ru_to_zh_front.html").read_text(encoding="utf-8")
    assert "onMistake" in script
    assert "onCorrectStroke" not in script
    assert "Черта не распознана" not in script
    assert "Черта принята" not in script
    assert "Осталось:" not in script
    assert "по одной черте" not in front
    assert "HANDWRITING_LENIENCY = 1.5" in script
    assert "acceptBackwardsStrokes: false" in script


def test_custom_show_answer_is_absent_and_check_button_hides():
    script = (ROOT / "web" / "card.js").read_text(encoding="utf-8")
    fronts = "\n".join(
        (ROOT / "templates" / name).read_text(encoding="utf-8")
        for name in ("ru_to_zh_front.html", "zh_to_ru_front.html")
    )
    assert "show-answer" not in fronts
    assert "answer-notice" not in fronts
    assert "requestShowAnswer" not in script
    assert 'getElementById("check-answer").hidden = writing.ok && pinyin.ok' in script
    assert 'getElementById("check-answer").hidden = russian.ok && pinyin.ok' in script


def test_hanzi_display_is_regular_weight_and_greeting_has_no_punctuation():
    css = (ROOT / "templates" / "style.css").read_text(encoding="utf-8")
    records = read_cards(ROOT / "data" / "cards.tsv")
    greeting = next(record for record in records if record.uid == "nihao-001")
    assert "font-weight: 400" in css
    assert greeting.hanzi == "你好"


def test_writer_squares_have_copybook_cross():
    css = (ROOT / "templates" / "style.css").read_text(encoding="utf-8")
    square = css.split(".writer-square {", 1)[1].split("}", 1)[0]
    assert square.count("repeating-linear-gradient") == 2
    assert "background-size: 1px 100%, 100% 1px;" in square


def test_erase_button_is_always_available():
    script = (ROOT / "web" / "card.js").read_text(encoding="utf-8")
    front = (ROOT / "templates" / "ru_to_zh_front.html").read_text(encoding="utf-8")
    assert 'type="button">Стереть</button>' in front
    assert 'getElementById("retry-writing").hidden' not in script
    assert 'getElementById("pinyin-status").textContent = ""' not in script
    assert 'getElementById("pinyin-input").value =' not in script


def test_hint_traces_the_answer_and_is_reported_after_check():
    script = (ROOT / "web" / "card.js").read_text(encoding="utf-8")
    front = (ROOT / "templates" / "ru_to_zh_front.html").read_text(encoding="utf-8")
    assert 'id="show-hint" class="secondary tappable" type="button">Подсказка</button>' in front
    assert "writer.animateCharacter({ onComplete: startQuiz })" in script
    assert script.count("showOutline: hintShown") == 2
    assert 'writing.message + ", с подсказкой"' in script
    assert "hintUsed: hintUsed" in script


def test_interactive_controls_are_ankidroid_touch_safe():
    script = (ROOT / "web" / "card.js").read_text(encoding="utf-8")
    fronts = [
        (ROOT / "templates" / name).read_text(encoding="utf-8")
        for name in (
            "ru_to_zh_front.html",
            "zh_to_ru_front.html",
        )
    ]
    assert 'addEventListener("touchend"' in script
    assert '{ passive: false }' in script
    assert all('id="check-answer" class="tappable"' in front for front in fronts)


def test_answer_inputs_request_no_keyboard_suggestions():
    fronts = "\n".join(
        (ROOT / "templates" / name).read_text(encoding="utf-8")
        for name in ("ru_to_zh_front.html", "zh_to_ru_front.html")
    )
    assert fronts.count('autocomplete="off"') == 3
    assert fronts.count('autocorrect="off"') == 3
    assert fronts.count('autocapitalize="none"') == 3
    assert fronts.count('spellcheck="false"') == 3
    # Keyboards ignore the attributes above; a former password field reaches Android as a
    # visible password, which hides the suggestion strip.
    assert fronts.count('id="pinyin-input" class="tappable" type="password"') == 2
    script = (ROOT / "web" / "card.js").read_text(encoding="utf-8")
    assert script.count("showPinyinInput();") == 2
    assert 'input.type = "text"' in script


def test_russian_prompts_do_not_reveal_cjk_characters_to_write():
    for source in ("cards.tsv", "radicals.tsv"):
        records = read_cards(ROOT / "data" / source)
        for record in records:
            answer_characters = {char for char in record.hanzi if is_cjk(char)}
            revealed_characters = {char for char in record.russian if is_cjk(char)}
            assert not (answer_characters & revealed_characters), record.uid


def test_particle_prompts_describe_their_function():
    records = {record.uid: record for record in read_cards(ROOT / "data" / "cards.tsv")}
    assert records["ma-particle-001"].russian == "частица вопроса с ответом «да/нет»"
    assert records["ne-001"].russian == "частица встречного вопроса"
    assert records["de-001"].russian == "частица принадлежности (указывает на обладание)"
    assert records["le-001"].russian == "частица завершённости действия или изменения состояния"
