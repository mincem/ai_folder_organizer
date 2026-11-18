import json

import pytest

from lib.command import Command
from lib.series_metadata import DEMOGRAPHICS, GENRES

FOLDERS = ["some series 1", "some series 2", "other series"]


def ai_entry(original, series="Some Series", volume=None, title=None):
    return {"original": original, "series": series, "volume": volume, "title": title, "notes": None}


def ai_series(series, **fields):
    return {"series": series, "writer": None, "penciller": None, "publisher": None, "imprint": None,
            "genre": [], "notes": None, **fields}


# get_prompt

def test_get_prompt_with_country():
    prompt = Command.get_prompt(FOLDERS, "XX")
    assert "published in XX" in prompt
    assert "\n".join(FOLDERS) in prompt
    assert GENRES[0] in prompt and DEMOGRAPHICS[0] in prompt
    for placeholder in ("{country}", "{genres}", "{demographics}", "{folders}"):
        assert placeholder not in prompt


def test_get_prompt_without_country_uses_original_publisher():
    prompt = Command.get_prompt(FOLDERS)
    assert "Publisher and imprint are the original ones" in prompt
    assert "which is published in" not in prompt


# parse_response

def test_parse_response_returns_object():
    assert Command.parse_response('{"entries": []}') == {"entries": []}


def test_parse_response_rejects_non_object():
    with pytest.raises(ValueError):
        Command.parse_response("[]")


def test_parse_response_rejects_invalid_json():
    with pytest.raises(json.JSONDecodeError):
        Command.parse_response("not json")


# validate_entries

def test_validate_entries_keeps_known_folders():
    entries = [ai_entry(folder) for folder in FOLDERS]
    assert Command.validate_entries(entries, FOLDERS) == entries


def test_validate_entries_rejects_non_list():
    with pytest.raises(ValueError):
        Command.validate_entries(None, FOLDERS)


def test_validate_entries_skips_bad_entries_with_warnings(capsys):
    entries = [
        ai_entry("some series 1"),
        ai_entry("some series 1"),             # repeated
        ai_entry("unknown folder"),            # not in the input
        "not a dict",
        ai_entry("some series 2", series="?"),  # empty after sanitizing
    ]                                          # "other series" is missing
    assert Command.validate_entries(entries, FOLDERS) == [entries[0]]

    output = capsys.readouterr().out
    assert "unknown or repeated folder 'some series 1'" in output
    assert "unknown or repeated folder 'unknown folder'" in output
    assert "unknown or repeated folder 'None'" in output
    assert "no series title for 'some series 2'" in output
    assert "nothing for 'other series'" in output


# validate_series

def test_validate_series_matches_titles_loosely_and_cleans_fields():
    entries = [ai_entry("a", series="Some Series")]
    items = [ai_series("some series!", writer=" Some Writer ", genre=["Action", "Drama"])]
    assert Command.validate_series(items, entries) == {
        "Some Series": {"writer": "Some Writer", "penciller": None, "publisher": None, "imprint": None,
                        "genre": "Action, Drama", "notes": None},
    }


def test_validate_series_ignores_unknown_and_repeated_and_warns_missing(capsys):
    entries = [ai_entry("a", series="Some Series"), ai_entry("b", series="Other Series")]
    items = [ai_series("Some Series", writer="First"), ai_series("Some Series", writer="Second"),
             ai_series("Unknown Series"), "not a dict"]
    metadata = Command.validate_series(items, entries)

    assert list(metadata) == ["Some Series"]
    assert metadata["Some Series"]["writer"] == "First"
    output = capsys.readouterr().out
    assert "unknown or repeated series 'Some Series'" in output
    assert "unknown or repeated series 'Unknown Series'" in output
    assert "no metadata for 'Other Series'" in output


def test_validate_series_non_list_returns_empty(capsys):
    assert Command.validate_series(None, [ai_entry("a")]) == {}
    assert "no series metadata" in capsys.readouterr().out
