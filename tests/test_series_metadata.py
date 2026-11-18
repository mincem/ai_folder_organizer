import pytest

from lib.series_metadata import clean_language, clean_series_item


def test_clean_series_item_keeps_known_fields_as_strings_or_none():
    item = {"series": "Some Series", "writer": "  Some Writer ", "penciller": "", "publisher": 42,
            "genre": ["Action", " Drama ", "Action", ""], "notes": "  ", "unknown_field": "x"}
    assert clean_series_item(item) == {"writer": "Some Writer", "penciller": None, "publisher": None,
                                       "imprint": None, "genre": "Action, Drama", "notes": None}


def test_clean_series_item_drops_unknown_genres_with_warning(capsys):
    item = {"series": "Some Series", "genre": ["Action", "Made Up Genre"]}
    assert clean_series_item(item)["genre"] == "Action"
    assert "ignoring unknown genre for 'Some Series': Made Up Genre" in capsys.readouterr().out


def test_clean_series_item_empty_genre_is_none():
    assert clean_series_item({"series": "Some Series", "genre": []})["genre"] is None


@pytest.mark.parametrize("language, expected", [
    ("xx", "xx"),
    (" XX ", "xx"),
    (None, None),
])
def test_clean_language(language, expected):
    assert clean_language(language) == expected


@pytest.mark.parametrize("language", ["xxx", "x1", "", 12])
def test_clean_language_invalid_warns(language, capsys):
    assert clean_language(language) is None
    assert "invalid language code" in capsys.readouterr().out
