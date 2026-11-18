import pytest

from lib.command import Command

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


def test_rejects_missing_directory(tmp_path):
    missing = str(tmp_path / "missing")
    with pytest.raises(ValueError):
        Command(missing, None, None, None, None)


def test_get_entries_builds_names_and_metadata(make_command):
    command = make_command(RESPONSE, country="XX")
    folders = ["some series 01", "some series 02"]
    entries, metadata = command.get_entries(folders)

    assert [(e["original"], e["new_name"], e["changes"]) for e in entries] == [
        ("some series 01", "Some Series v01", []),
        ("some series 02", "Some Series v02 [Part - Two]", ["replaced ':' with '-'"]),
    ]
    assert metadata == {"Some Series": {
        "language_iso": "xx", "writer": "Some Writer", "penciller": None, "publisher": "Some Publisher",
        "imprint": None, "genre": "Action", "notes": None,
    }}
    assert len(command.fake_client.prompts) == 1
    assert "some series 01\nsome series 02" in command.fake_client.prompts[0]


def test_get_entries_saves_ai_log(make_command, tmp_path):
    make_command(RESPONSE).get_entries(["some series 01", "some series 02"])
    logs = list((tmp_path / "logs").iterdir())
    assert len(logs) == 1
    assert "Some Series" in logs[0].read_text(encoding="utf-8")


def test_execute_without_folders_does_not_ask_ai(make_command):
    command = make_command(RESPONSE)
    command.execute()
    assert command.fake_client.prompts == []
