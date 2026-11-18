"""Deciding what to rename: skipping conflicts, grouping by series and warning about gaps."""
import os
from collections import Counter

from .entry import Entry
from .naming import normalize


def drop_conflicts(entries: list[Entry], root_folder: str) -> list[Entry]:
    """Returns the entries that can be renamed, warning about the ones skipped."""
    # Windows names are case-insensitive, so compare them casefolded
    targets = Counter(entry.new_name.casefold() for entry in entries
                      if entry.new_name != entry.original)

    valid = []
    for entry in entries:
        original, new_name = entry.original, entry.new_name
        is_case_only_change = original.casefold() == new_name.casefold()
        if original == new_name:
            valid.append(entry)
        elif targets[new_name.casefold()] > 1:
            print(f"Warning: more than one folder would be renamed to '{new_name}', skipping '{original}'.")
        elif not is_case_only_change and os.path.exists(os.path.join(root_folder, new_name)):
            print(f"Warning: '{new_name}' already exists, skipping '{original}'.")
        else:
            valid.append(entry)
    return valid


def group_by_series(entries: list[Entry]) -> dict[str, list[Entry]]:
    groups = {}
    for entry in entries:
        groups.setdefault(entry.series, []).append(entry)
    for group in groups.values():
        group.sort(key=lambda e: (e.volume is None, e.volume or 0, e.original))
    return groups


def series_warnings(series: str, group: list[Entry], all_series: list[str]) -> list[str]:
    warnings = []
    volumes = [entry.volume for entry in group if entry.volume is not None]

    repeated = sorted(volume for volume, count in Counter(volumes).items() if count > 1)
    if repeated:
        warnings.append(f"repeated volumes: {', '.join(f'v{v:02d}' for v in repeated)}")

    if volumes:
        missing = sorted(set(range(min(volumes), max(volumes) + 1)) - set(volumes))
        if len(missing) > 10:
            warnings.append(f"{len(missing)} missing volumes between v{min(volumes):02d} and v{max(volumes):02d}")
        elif missing:
            warnings.append(f"missing volumes: {', '.join(f'v{v:02d}' for v in missing)}")

    # The AI may split one series in two by spelling it differently
    similar = [other for other in all_series
               if other != series and normalize(other) == normalize(series)]
    if similar:
        warnings.append(f"similar series title: {', '.join(repr(other) for other in similar)}")
    return warnings
