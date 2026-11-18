from lib.planning import add_new_names, group_by_series, series_warnings


def entry(original, series="Some Series", volume=None):
    return {"original": original, "series": series, "volume": volume}


def test_add_new_names_sets_name_and_changes():
    entries = [
        {"original": "a", "series": "Some Series", "volume": 1, "title": None},
        {"original": "b", "series": "Some: Series", "volume": 2, "title": "Part: Two?"},
    ]
    add_new_names(entries)
    assert [(e["new_name"], e["changes"]) for e in entries] == [
        ("Some Series v01", []),
        ("Some - Series v02 [Part - Two]", ["replaced ':' with '-'", "removed '?'"]),
    ]


def test_group_by_series_sorts_by_volume_then_unnumbered_by_name():
    entries = [
        entry("b", volume=None),
        entry("c", volume=2),
        entry("x", series="Other Series", volume=1),
        entry("a", volume=None),
        entry("d", volume=1),
    ]
    groups = group_by_series(entries)
    assert list(groups) == ["Some Series", "Other Series"]
    assert [e["original"] for e in groups["Some Series"]] == ["d", "c", "a", "b"]


def test_series_warnings_none_for_complete_series():
    group = [entry("a", volume=1), entry("b", volume=2), entry("c", volume=None)]
    assert series_warnings("Some Series", group, ["Some Series"]) == []


def test_series_warnings_repeated_and_missing_volumes():
    group = [entry(str(v), volume=v) for v in (1, 1, 2, 4, 6)]
    assert series_warnings("Some Series", group, ["Some Series"]) == [
        "repeated volumes: v01",
        "missing volumes: v03, v05",
    ]


def test_series_warnings_summarizes_many_missing_volumes():
    group = [entry("a", volume=1), entry("b", volume=20)]
    assert series_warnings("Some Series", group, ["Some Series"]) == [
        "18 missing volumes between v01 and v20",
    ]


def test_series_warnings_similar_titles():
    all_series = ["Some Series", "Some series!", "Other Series"]
    assert series_warnings("Some Series", [entry("a")], all_series) == [
        "similar series title: 'Some series!'",
    ]
