import pytest

from lib.command import Command


def test_rejects_missing_directory(tmp_path):
    missing = str(tmp_path / "missing")
    with pytest.raises(ValueError):
        Command(missing, None, None, None, None, None)


def test_execute_without_folders_does_not_ask_ai(make_command):
    command = make_command({})
    command.execute()
    assert command.fake_client.prompts == []
