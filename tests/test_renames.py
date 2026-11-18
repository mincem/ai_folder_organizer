import sys

import pytest

from lib.entry import Entry
from lib.planning import drop_conflicts


# drop_conflicts

def test_drop_conflicts_keeps_unchanged_and_free_targets(comics_dir):
    entries = [Entry("Some Series v01", "Some Series", 1), Entry("some series 2", "Some Series", 2)]
    assert drop_conflicts(entries, str(comics_dir)) == entries


def test_drop_conflicts_skips_all_entries_with_the_same_target(comics_dir, capsys):
    # "some series v01" and "Some Series v01" are the same name on Windows
    entries = [Entry("a", "Some Series", 1), Entry("b", "some series", 1), Entry("c", "Some Series", 2)]
    assert drop_conflicts(entries, str(comics_dir)) == [entries[2]]
    output = capsys.readouterr().out
    assert "skipping 'a'" in output and "skipping 'b'" in output


def test_drop_conflicts_skips_existing_target(comics_dir, capsys):
    (comics_dir / "Some Series v01").mkdir()
    entries = [Entry("some series 1", "Some Series", 1)]
    assert drop_conflicts(entries, str(comics_dir)) == []
    assert "'Some Series v01' already exists, skipping 'some series 1'" in capsys.readouterr().out


def test_drop_conflicts_allows_case_only_change(comics_dir):
    # On Windows the target "exists", because it's the same folder
    (comics_dir / "some series v01").mkdir()
    entries = [Entry("some series v01", "Some Series", 1)]
    assert drop_conflicts(entries, str(comics_dir)) == entries


# rename_folder

def test_rename_folder(make_command, comics_dir):
    (comics_dir / "some series 1").mkdir()
    command = make_command()
    command.rename_folder("some series 1", "Some Series v01")
    assert [p.name for p in comics_dir.iterdir()] == ["Some Series v01"]
    assert command.logger.successful_renames == 1


@pytest.mark.skipif(sys.platform != "win32", reason="case-insensitive file system")
def test_rename_folder_case_only(make_command, comics_dir):
    (comics_dir / "some series v01").mkdir()
    make_command().rename_folder("some series v01", "Some Series v01")
    assert [p.name for p in comics_dir.iterdir()] == ["Some Series v01"]


def test_rename_folder_missing_original_warns(make_command, capsys):
    command = make_command()
    command.rename_folder("missing", "Some Series v01")
    assert "'missing' not found" in capsys.readouterr().out
    assert command.logger.successful_renames == 0


def test_rename_folder_error_is_reported(make_command, comics_dir, capsys):
    (comics_dir / "some series 1").mkdir()
    (comics_dir / "Some Series v01").mkdir()
    (comics_dir / "Some Series v01" / "file.txt").write_text("x")  # not empty, so it can't be replaced
    command = make_command()
    command.rename_folder("some series 1", "Some Series v01")
    assert "Error renaming 'some series 1'" in capsys.readouterr().out
    assert (comics_dir / "some series 1").exists()
    assert command.logger.successful_renames == 0
