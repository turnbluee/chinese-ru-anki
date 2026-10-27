import pytest

from pinyin import normalize_pinyin, pinyin_matches, validate_stored_pinyin


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("zhi1dao4", "zhi1dao4"),
        (" ZHI1 DAO4 ", "zhi1dao4"),
        ("nv3", "nv3"),
        ("nü3", "nv3"),
        ("lv4", "lv4"),
        ("lü4", "lv4"),
        ("ma0", "ma0"),
    ],
)
def test_normalize_pinyin(raw, expected):
    assert normalize_pinyin(raw) == expected


@pytest.mark.parametrize("value", ["nǐ", "zhīdào", "xuésheng"])
def test_reject_tone_marks(value):
    assert pinyin_matches(value, "ni3")[0] is False
    assert "номерами" in pinyin_matches(value, "ni3")[1]


@pytest.mark.parametrize("value", ["ni", "zhidao", "zhi1dao"])
def test_reject_missing_tone_number(value):
    assert validate_stored_pinyin(value) is not None


def test_pinyin_match_accepts_spaces_case_and_umlaut():
    assert pinyin_matches(" ZHI1 DAO4 ", "zhi1dao4")[0]
    assert pinyin_matches("nü3", "nv3")[0]


@pytest.mark.parametrize(
    "value",
    [
        "zhi1dao4",
        "ni3",
        "xue2sheng0",
        "piao4liang0",
        "ma0",
        "de0",
        "le0",
        "nv3",
        "nü3",
        "lv4",
        "lü4",
    ],
)
def test_required_numeric_pinyin_is_accepted(value):
    expected = value.replace("ü", "v")
    assert validate_stored_pinyin(expected) is None
    assert pinyin_matches(value, expected)[0]


@pytest.mark.parametrize("value", ["ma5", "de5", "le5", "xue2sheng5", "piao4liang5"])
def test_tone_five_is_rejected_and_not_converted(value):
    assert normalize_pinyin(value) == value
    assert "тон 5" in validate_stored_pinyin(value)
    ok, message = pinyin_matches(value, value.replace("5", "0"))
    assert not ok
    assert "5" in message
