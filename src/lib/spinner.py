"""A block bouncing inside brackets after a line of text, to show the program is waiting: "Asking... [  ■   ]"."""
import sys
import threading

WIDTH = 8
BLOCK = '■'
INTERVAL = 0.12


def frames(width: int = WIDTH) -> list[str]:
    """One full back-and-forth: the block goes right, then left, without repeating the ends."""
    positions = list(range(width)) + list(range(width - 2, 0, -1))
    return [f"[{' ' * i}{BLOCK}{' ' * (width - 1 - i)}]" for i in positions]


class Spinner:
    """Prints the text, animates after it while the block runs, then erases the animation.

    The cursor is left right after the text, so the caller can finish the line (e.g. print(" done")).
    Only animates in a terminal; when the output is redirected (logs, tests) it just prints the text."""

    def __init__(self, text: str, stream=None):
        self.text = text
        self.stream = stream or sys.stdout
        self.stop_event = threading.Event()
        self.thread = None

    def __enter__(self):
        self.stream.write(self.text)
        self.stream.flush()
        if self.stream.isatty():
            self.thread = threading.Thread(target=self.animate, daemon=True)
            self.thread.start()
        return self

    def __exit__(self, *exc):
        if self.thread:
            self.stop_event.set()
            self.thread.join()
            # Blank out the animation and go back to the end of the text
            self.stream.write(f"\r{self.text}{' ' * (WIDTH + 3)}\r{self.text}")
            self.stream.flush()
        return False

    def animate(self):
        all_frames = frames()
        i = 0
        while not self.stop_event.is_set():
            self.stream.write(f"\r{self.text} {all_frames[i % len(all_frames)]}")
            self.stream.flush()
            i += 1
            self.stop_event.wait(INTERVAL)
