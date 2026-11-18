import pytest

from lib.command import Command


@pytest.mark.parametrize("text, expected", [
    ("Some Series", "Some Series"),
    ("Some Series: The Sequel", "Some Series - The Sequel"),
    ('Some <Series> "Name"?', "Some Series Name"),
    ("Back\\Slash/Pipe|Star*", "BackSlashPipeStar"),
    ("Some   Series", "Some Series"),
    ("Some Series. ", "Some Series"),
    ("Some Series...", "Some Series"),
    ("???", ""),
])
def test_sanitize(text, expected):
    assert Command.sanitize(text) == expected


def test_describe_sanitize_lists_each_change():
    assert Command.describe_sanitize("Some: Series?*.") == [
        "replaced ':' with '-'",
        "removed '*', '?'",
        "removed trailing '.'",
    ]


def test_describe_sanitize_clean_text_has_no_changes():
    assert Command.describe_sanitize("Some Series") == []


@pytest.mark.parametrize("entry, expected", [
    ({"series": "Some Series", "volume": 3, "title": "Some Book"}, "Some Series v03 [Some Book]"),
    ({"series": "Some Series", "volume": 12, "title": None}, "Some Series v12"),
    ({"series": "Some Series", "volume": 123, "title": None}, "Some Series v123"),
    ({"series": "Some Series", "volume": None, "title": "Some Book"}, "Some Series [Some Book]"),
    ({"series": "Some Series", "volume": None, "title": None}, "Some Series"),
    ({"series": "Some Series", "volume": 0, "title": ""}, "Some Series v00"),
    ({"series": "Some: Series", "volume": 1, "title": "Part: One?"}, "Some - Series v01 [Part - One]"),
])
def test_build_new_name(entry, expected):
    assert Command.build_new_name(entry) == expected


def test_normalize_ignores_case_accents_and_punctuation():
    assert Command.normalize("Sérïes: Ñame!") == Command.normalize("series name")
    assert Command.normalize("Some Series") != Command.normalize("Other Series")
