import json

import pytest

from lib.metadata_cache import FILE_NAME, MetadataCache

SOME_METADATA = {"country": "XX", "writer": "Some Writer"}


def test_missing_file_starts_empty(tmp_path):
    cache = MetadataCache(str(tmp_path))
    assert cache.get("Some Series") is None
    assert not (tmp_path / FILE_NAME).exists()


def test_set_saves_sorted_and_reloads(tmp_path):
    cache = MetadataCache(str(tmp_path))
    cache.set("Some Series", SOME_METADATA)
    cache.set("Other Series", {"country": None})

    saved = json.loads((tmp_path / FILE_NAME).read_text(encoding="utf-8"))
    assert list(saved) == ["Other Series", "Some Series"]
    assert MetadataCache(str(tmp_path)).get("Some Series") == SOME_METADATA
    assert not (tmp_path / (FILE_NAME + ".tmp")).exists()


def test_keeps_non_ascii_readable(tmp_path):
    MetadataCache(str(tmp_path)).set("Sérïes", SOME_METADATA)
    assert "Sérïes" in (tmp_path / FILE_NAME).read_text(encoding="utf-8")


@pytest.mark.parametrize("content", ["{not json", "[]"])
def test_unreadable_file_raises_and_is_not_overwritten(tmp_path, content):
    path = tmp_path / FILE_NAME
    path.write_text(content, encoding="utf-8")
    with pytest.raises(ValueError):
        MetadataCache(str(tmp_path))
    assert path.read_text(encoding="utf-8") == content
