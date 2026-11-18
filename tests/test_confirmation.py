"""The Confirmer on its own. The full flow of questions is covered through Command in test_execute.py."""
from lib.confirmation import Confirmer, same_country
from lib.metadata_cache import FILE_NAME, MetadataCache

SOME_METADATA = {"language_iso": "xx", "writer": "Some Writer", "penciller": None, "publisher": None,
                 "imprint": None, "genre": "Action", "notes": None}


def entry(original, new_name, volume):
    return {"original": original, "new_name": new_name, "series": "Some Series", "volume": volume,
            "changes": [], "notes": None}


def test_confirm_returns_accepted_renames_and_metadata_without_saving(comics_dir, answers):
    entries = [entry("some series 1", "Some Series v01", 1), entry("some series 2", "Some Series v02", 2)]
    answers("y")
    confirmer = Confirmer(MetadataCache(str(comics_dir)), "XX")

    approved, metadata_to_save = confirmer.confirm(entries, entries, {"Some Series": SOME_METADATA})

    assert approved == entries
    assert metadata_to_save == {"Some Series": SOME_METADATA}
    assert not (comics_dir / FILE_NAME).exists()


def test_same_country_ignores_case_spaces_and_none():
    assert same_country(" xx", "XX ")
    assert same_country(None, "")
    assert not same_country("XX", "YY")
