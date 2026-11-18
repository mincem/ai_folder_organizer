"""The whole run: folders on disk -> fake AI -> scripted answers -> renamed folders and saved metadata."""
import json

from lib.ai_client import AIError
from lib.metadata_cache import FILE_NAME

SOME_SERIES_FIELDS = {"writer": "Some Writer", "penciller": None, "publisher": "Some Publisher",
                      "imprint": None, "genre": ["Action"], "notes": None}
SAVED_METADATA = {"country": "XX", "language_iso": "xx", **SOME_SERIES_FIELDS, "genre": "Action"}


def response(*entries, series=("Some Series",)):
    """entries are (original, series, volume) tuples."""
    return {
        "entries": [{"original": original, "series": name, "volume": volume, "title": None, "notes": None}
                    for original, name, volume in entries],
        "series": [{"series": name, **SOME_SERIES_FIELDS} for name in series],
        "language_iso": "xx",
    }


TWO_VOLUMES = response(("some series 1", "Some Series", 1), ("some series 2", "Some Series", 2))


def make_folders(comics_dir, *names):
    for name in names:
        (comics_dir / name).mkdir()


def folders(comics_dir):
    return sorted(p.name for p in comics_dir.iterdir() if p.is_dir())


def saved_metadata(comics_dir):
    path = comics_dir / FILE_NAME
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def questions(prompts):
    return [prompt.split("?")[0] for prompt in prompts]


# A series with several folders

def test_accepting_series_renames_all_and_saves_metadata(make_command, comics_dir, answers):
    make_folders(comics_dir, "some series 1", "some series 2")
    prompts = answers("")
    make_command(TWO_VOLUMES, country="XX").execute()

    assert questions(prompts) == ["Rename all"]
    assert folders(comics_dir) == ["Some Series v01", "Some Series v02"]
    assert saved_metadata(comics_dir) == {"Some Series": SAVED_METADATA}


def test_rejecting_series_changes_nothing(make_command, comics_dir, answers):
    make_folders(comics_dir, "some series 1", "some series 2")
    answers("n")
    make_command(TWO_VOLUMES, country="XX").execute()

    assert folders(comics_dir) == ["some series 1", "some series 2"]
    assert saved_metadata(comics_dir) == {}


def test_reviewing_series_asks_each_folder(make_command, comics_dir, answers):
    make_folders(comics_dir, "some series 1", "some series 2")
    prompts = answers("r", "y", "n")
    make_command(TWO_VOLUMES, country="XX").execute()

    assert questions(prompts) == ["Rename all", "Rename", "Rename"]
    assert folders(comics_dir) == ["Some Series v01", "some series 2"]
    # One accepted folder is enough to save the series metadata
    assert saved_metadata(comics_dir) == {"Some Series": SAVED_METADATA}


def test_unknown_answer_asks_again(make_command, comics_dir, answers):
    make_folders(comics_dir, "some series 1", "some series 2")
    prompts = answers("maybe", "y")
    make_command(TWO_VOLUMES).execute()

    assert questions(prompts) == ["Rename all", "Rename all"]
    assert folders(comics_dir) == ["Some Series v01", "Some Series v02"]


# A series with a single folder

def test_single_folder_asks_once(make_command, comics_dir, answers):
    make_folders(comics_dir, "some series 1")
    prompts = answers("n")
    make_command(response(("some series 1", "Some Series", 1))).execute()

    assert questions(prompts) == ["Rename"]
    assert folders(comics_dir) == ["some series 1"]
    assert saved_metadata(comics_dir) == {}


def test_each_series_is_asked_separately(make_command, comics_dir, answers):
    make_folders(comics_dir, "some series 1", "other series 1")
    ai_response = response(("some series 1", "Some Series", 1), ("other series 1", "Other Series", 1),
                           series=("Some Series", "Other Series"))
    prompts = answers("y", "n")
    make_command(ai_response, country="XX").execute()

    assert questions(prompts) == ["Rename", "Rename"]
    assert folders(comics_dir) == ["Some Series v01", "other series 1"]
    assert list(saved_metadata(comics_dir)) == ["Some Series"]


# Folders that already have the right name

def test_right_names_only_ask_for_metadata(make_command, comics_dir, answers, capsys):
    make_folders(comics_dir, "Some Series v01", "Some Series v02")
    ai_response = response(("Some Series v01", "Some Series", 1), ("Some Series v02", "Some Series", 2))
    prompts = answers("y")
    make_command(ai_response, country="XX").execute()

    assert questions(prompts) == ["Save metadata"]
    assert "2 folders already have the right name" in capsys.readouterr().out
    assert saved_metadata(comics_dir) == {"Some Series": SAVED_METADATA}


def test_saved_metadata_for_same_country_is_kept_without_asking(make_command, comics_dir, answers):
    make_folders(comics_dir, "Some Series v01")
    old = {"Some Series": {"country": "xx", "writer": "Old Writer"}}
    (comics_dir / FILE_NAME).write_text(json.dumps(old), encoding="utf-8")
    answers()
    make_command(response(("Some Series v01", "Some Series", 1)), country="XX").execute()

    assert saved_metadata(comics_dir) == old


def test_saved_metadata_for_other_country_is_offered_again(make_command, comics_dir, answers, capsys):
    make_folders(comics_dir, "Some Series v01")
    old = {"Some Series": {"country": "YY", "writer": "Old Writer"}}
    (comics_dir / FILE_NAME).write_text(json.dumps(old), encoding="utf-8")
    prompts = answers("y")
    make_command(response(("Some Series v01", "Some Series", 1)), country="XX").execute()

    assert questions(prompts) == ["Save metadata"]
    assert "replaces the saved metadata for country: YY" in capsys.readouterr().out
    assert saved_metadata(comics_dir) == {"Some Series": SAVED_METADATA}


# Conflicts and errors

def test_conflicting_folders_are_not_asked(make_command, comics_dir, answers, capsys):
    make_folders(comics_dir, "some series 1", "some series one")
    ai_response = response(("some series 1", "Some Series", 1), ("some series one", "Some Series", 1))
    answers()
    make_command(ai_response).execute()

    assert folders(comics_dir) == ["some series 1", "some series one"]
    assert "right name" not in capsys.readouterr().out
    assert saved_metadata(comics_dir) == {}


def test_metadata_is_offered_when_one_folder_is_right_and_another_conflicts(make_command, comics_dir, answers):
    make_folders(comics_dir, "Some Series v01", "some series 1", "some series one")
    ai_response = response(("Some Series v01", "Some Series", 1), ("some series 1", "Some Series", 2),
                           ("some series one", "Some Series", 2))
    prompts = answers("y")
    make_command(ai_response, country="XX").execute()

    assert questions(prompts) == ["Save metadata"]
    assert folders(comics_dir) == ["Some Series v01", "some series 1", "some series one"]
    assert saved_metadata(comics_dir) == {"Some Series": SAVED_METADATA}


def test_ai_error_changes_nothing(make_command, comics_dir, answers, capsys):
    make_folders(comics_dir, "some series 1")
    answers()
    make_command(AIError("quota exceeded")).execute()

    assert "Error getting a response from the AI: quota exceeded" in capsys.readouterr().out
    assert folders(comics_dir) == ["some series 1"]


def test_temporary_ai_error_offers_retry_that_can_succeed(make_command, comics_dir, answers):
    make_folders(comics_dir, "some series 1", "some series 2")
    prompts = answers("", "")
    command = make_command([AIError("overloaded", retryable=True), TWO_VOLUMES])
    command.execute()

    assert questions(prompts) == ["Try again", "Rename all"]
    assert len(command.fake_client.prompts) == 2
    assert folders(comics_dir) == ["Some Series v01", "Some Series v02"]


def test_declining_retry_changes_nothing(make_command, comics_dir, answers):
    make_folders(comics_dir, "some series 1")
    prompts = answers("n")
    command = make_command([AIError("overloaded", retryable=True)])
    command.execute()

    assert questions(prompts) == ["Try again"]
    assert len(command.fake_client.prompts) == 1
    assert folders(comics_dir) == ["some series 1"]


def test_retry_with_other_model_uses_the_chosen_one(make_command, comics_dir, answers, capsys):
    make_folders(comics_dir, "some series 1", "some series 2")
    # The list leaves out the current model, so "2" is the third one
    prompts = answers("o", "9", "2", "")
    command = make_command([AIError("overloaded", retryable=True), TWO_VOLUMES])
    command.execute()

    assert questions(prompts) == ["Try again", "Model number (Enter to cancel): ",
                                  "Model number (Enter to cancel): ", "Rename all"]
    assert "1. other-model" in capsys.readouterr().out
    assert command.fake_client.models == ["models/fake-model", "models/third-model"]
    assert folders(comics_dir) == ["Some Series v01", "Some Series v02"]


def test_cancelling_model_choice_asks_retry_again(make_command, comics_dir, answers):
    make_folders(comics_dir, "some series 1")
    prompts = answers("o", "", "n")
    command = make_command([AIError("overloaded", retryable=True)])
    command.execute()

    assert questions(prompts) == ["Try again", "Model number (Enter to cancel): ", "Try again"]
    assert command.fake_client.models == ["models/fake-model"]
    assert folders(comics_dir) == ["some series 1"]


def test_invalid_response_changes_nothing(make_command, comics_dir, answers, capsys):
    make_folders(comics_dir, "some series 1")
    answers()
    make_command("not json").execute()

    assert "Error parsing AI response" in capsys.readouterr().out
    assert folders(comics_dir) == ["some series 1"]
