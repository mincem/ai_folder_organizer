import json

import pytest

from lib.ai_request import get_prompt, parse_response, validate_entries, validate_series
from lib.entry import Entry
from lib.series_metadata import DEMOGRAPHICS, GENRES

FOLDERS = ["some series 1", "some series 2", "other series"]


def ai_entry(original, series="Some Series", volume=None, title=None):
    return {"original": original, "series": series, "volume": volume, "title": title, "notes": None}


RESPONSE = {
    "entries": [
        {"original": "some series 01", "series": "Some Series", "volume": 1, "title": None, "notes": None},
        {"original": "some series 02", "series": "Some Series", "volume": 2, "title": "Part: Two", "notes": None},
    ],
    "series": [
        {"series": "Some Series", "writer": "Some Writer", "penciller": None, "publisher": "Some Publisher",
         "imprint": None, "genre": ["Action"], "notes": None},
    ],
    "language_iso": "XX",
}


def ai_series(series, **fields):
    return {"series": series, "writer": None, "penciller": None, "publisher": None, "imprint": None,
            "genre": [], "notes": None, **fields}


# AIRequest.get_entries

def test_get_entries_returns_entries_and_metadata(make_ai_request):
    ai_request = make_ai_request(RESPONSE)
    entries, metadata = ai_request.get_entries(["some series 01", "some series 02"], "root", "XX")

    assert entries == [
        Entry("some series 01", "Some Series", 1),
        Entry("some series 02", "Some Series", 2, "Part: Two"),
    ]
    assert metadata == {"Some Series": {
        "language_iso": "xx", "writer": "Some Writer", "penciller": None, "publisher": "Some Publisher",
        "imprint": None, "genre": "Action", "notes": None,
    }}
    assert len(ai_request.fake_client.prompts) == 1
    assert "some series 01\nsome series 02" in ai_request.fake_client.prompts[0]
    assert "published in XX" in ai_request.fake_client.prompts[0]


def test_get_entries_saves_ai_log(make_ai_request, tmp_path):
    make_ai_request(RESPONSE).get_entries(["some series 01", "some series 02"], "some root", "XX")
    logs = list((tmp_path / "logs").iterdir())
    assert len(logs) == 1
    log = logs[0].read_text(encoding="utf-8")
    assert "Some Series" in log
    assert "- Folder: some root" in log and "- Country: XX" in log


# get_prompt

def test_get_prompt_with_country():
    prompt = get_prompt(FOLDERS, "XX")
    assert "published in XX" in prompt
    assert "\n".join(FOLDERS) in prompt
    assert GENRES[0] in prompt and DEMOGRAPHICS[0] in prompt
    for placeholder in ("{country}", "{genres}", "{demographics}", "{folders}"):
        assert placeholder not in prompt


def test_get_prompt_without_country_uses_original_publisher():
    prompt = get_prompt(FOLDERS)
    assert "Publisher and imprint are the original ones" in prompt
    assert "which is published in" not in prompt


# parse_response

def test_parse_response_returns_object():
    assert parse_response('{"entries": []}') == {"entries": []}


def test_parse_response_rejects_non_object():
    with pytest.raises(ValueError):
        parse_response("[]")


def test_parse_response_rejects_invalid_json():
    with pytest.raises(json.JSONDecodeError):
        parse_response("not json")


# validate_entries

def test_validate_entries_turns_known_folders_into_entries():
    entries = [ai_entry(folder, volume=i) for i, folder in enumerate(FOLDERS)]
    assert validate_entries(entries, FOLDERS) == [Entry(folder, "Some Series", i) for i, folder in enumerate(FOLDERS)]


def test_validate_entries_cleans_title_and_notes():
    entries = [
        {"original": "some series 1", "series": "Some Series", "volume": None, "title": "  ", "notes": " Check it "},
        {"original": "some series 2", "series": "Some Series", "title": 12},
    ]
    assert validate_entries(entries, FOLDERS[:2]) == [
        Entry("some series 1", "Some Series", None, None, "Check it"),
        Entry("some series 2", "Some Series"),
    ]


@pytest.mark.parametrize("volume", ["1", 1.5, True])
def test_validate_entries_skips_invalid_volume(volume, capsys):
    assert validate_entries([ai_entry("some series 1", volume=volume)], ["some series 1"]) == []
    assert f"invalid volume {volume!r} for 'some series 1'" in capsys.readouterr().out


def test_validate_entries_skips_non_string_series(capsys):
    assert validate_entries([ai_entry("some series 1", series=12)], ["some series 1"]) == []
    assert "no series title for 'some series 1'" in capsys.readouterr().out


def test_validate_entries_rejects_non_list():
    with pytest.raises(ValueError):
        validate_entries(None, FOLDERS)


def test_validate_entries_skips_bad_entries_with_warnings(capsys):
    entries = [
        ai_entry("some series 1"),
        ai_entry("some series 1"),             # repeated
        ai_entry("unknown folder"),            # not in the input
        "not a dict",
        ai_entry("some series 2", series="?"),  # empty after sanitizing
    ]                                          # "other series" is missing
    assert validate_entries(entries, FOLDERS) == [Entry("some series 1", "Some Series")]

    output = capsys.readouterr().out
    assert "unknown or repeated folder 'some series 1'" in output
    assert "unknown or repeated folder 'unknown folder'" in output
    assert "unknown or repeated folder 'None'" in output
    assert "no series title for 'some series 2'" in output
    assert "nothing for 'other series'" in output


# validate_series

def test_validate_series_matches_titles_loosely_and_cleans_fields():
    entries = [Entry("a", "Some Series")]
    items = [ai_series("some series!", writer=" Some Writer ", genre=["Action", "Drama"])]
    assert validate_series(items, entries) == {
        "Some Series": {"writer": "Some Writer", "penciller": None, "publisher": None, "imprint": None,
                        "genre": "Action, Drama", "notes": None},
    }


def test_validate_series_ignores_unknown_and_repeated_and_warns_missing(capsys):
    entries = [Entry("a", "Some Series"), Entry("b", "Other Series")]
    items = [ai_series("Some Series", writer="First"), ai_series("Some Series", writer="Second"),
             ai_series("Unknown Series"), "not a dict"]
    metadata = validate_series(items, entries)

    assert list(metadata) == ["Some Series"]
    assert metadata["Some Series"]["writer"] == "First"
    output = capsys.readouterr().out
    assert "unknown or repeated series 'Some Series'" in output
    assert "unknown or repeated series 'Unknown Series'" in output
    assert "no metadata for 'Other Series'" in output


def test_validate_series_non_list_returns_empty(capsys):
    assert validate_series(None, [Entry("a", "Some Series")]) == {}
    assert "no series metadata" in capsys.readouterr().out
