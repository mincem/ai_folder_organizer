import dataclasses

import pytest

from lib.entry import Entry


def test_new_name_and_changes():
    entry = Entry("b", "Some: Series", 2, "Part: Two?")
    assert entry.new_name == "Some - Series v02 [Part - Two]"
    assert entry.changes == ["replaced ':' with '-'", "removed '?'"]


def test_clean_name_has_no_changes():
    entry = Entry("a", "Some Series", 1)
    assert entry.new_name == "Some Series v01"
    assert entry.changes == []


def test_is_read_only():
    with pytest.raises(dataclasses.FrozenInstanceError):
        Entry("a", "Some Series").series = "Other Series"
