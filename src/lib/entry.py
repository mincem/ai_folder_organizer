from dataclasses import dataclass

from .naming import build_new_name, describe_sanitize


@dataclass(frozen=True)
class Entry:
    """One folder and what the AI says it is. Built from the AI response in ai_request.validate_entries."""
    original: str
    series: str
    volume: int | None = None
    title: str | None = None
    notes: str | None = None

    @property
    def new_name(self) -> str:
        return build_new_name(self.series, self.volume, self.title)

    @property
    def changes(self) -> list[str]:
        """What was changed to make the name valid on Windows, to show the user."""
        changes = describe_sanitize(self.series) + describe_sanitize(self.title or '')
        return list(dict.fromkeys(changes))
