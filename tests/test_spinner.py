import io

from lib.spinner import BLOCK, Spinner, frames


def test_frames_bounce_back_and_forth():
    all_frames = frames(width=3)

    assert all_frames == [f"[{BLOCK}  ]", f"[ {BLOCK} ]", f"[  {BLOCK}]", f"[ {BLOCK} ]"]


def test_without_terminal_only_prints_text():
    stream = io.StringIO()
    with Spinner("Asking...", stream):
        pass

    assert stream.getvalue() == "Asking..."


class FakeTerminal(io.StringIO):
    def isatty(self):
        return True


def test_in_terminal_ends_right_after_text():
    stream = FakeTerminal()
    with Spinner("Asking...", stream):
        pass

    assert stream.getvalue().endswith("\rAsking...")
