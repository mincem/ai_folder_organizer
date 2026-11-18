"""Asking the user which renames and series metadata to apply."""
from .entry import Entry
from .metadata_cache import MetadataCache
from .planning import group_by_series, series_warnings
from .series_metadata import SERIES_FIELDS


class Confirmer:
    """Only reads the metadata cache: saving what the user accepted is up to the caller."""

    def __init__(self, metadata_cache: MetadataCache, country: str | None):
        self.metadata_cache = metadata_cache
        self.country = country

    def confirm(self, entries: list[Entry], renamable: list[Entry],
                metadata: dict[str, dict]) -> tuple[list[Entry], dict[str, dict]]:
        """Returns the accepted entries to rename and the accepted metadata to save, keyed by series."""
        to_rename = {entry.original for entry in renamable if entry.new_name != entry.original}
        # Folders dropped for a conflict are in neither set
        unchanged = {entry.original for entry in renamable if entry.new_name == entry.original}
        if unchanged:
            print(f"\n{len(unchanged)} folders already have the right name.")

        # Group all entries, not only the renamable ones, so warnings consider the whole series
        groups = group_by_series(entries)
        cached = [series for series in groups if self.is_cached(series)]
        if cached:
            print(f"{len(cached)} series already have saved metadata, keeping it.")

        approved = []
        metadata_to_save = {}
        for series, group in groups.items():
            pending = [entry for entry in group if entry.original in to_rename]
            new_metadata = None if series in cached else metadata.get(series)
            if not pending:
                # Only offered when some folder is already right, not when all were skipped for conflicts
                has_unchanged = any(entry.original in unchanged for entry in group)
                if new_metadata and has_unchanged and self.confirm_metadata(series, new_metadata):
                    metadata_to_save[series] = new_metadata
                continue
            warnings = series_warnings(series, group, list(groups))
            if len(pending) == 1:
                confirmed = self.confirm_each(pending, warnings, new_metadata)
            else:
                confirmed = self.confirm_series(series, pending, warnings, new_metadata)
            # A single yes/no covers both the renames and the metadata
            if confirmed and new_metadata:
                metadata_to_save[series] = new_metadata
            approved += confirmed
        return approved, metadata_to_save

    def confirm_series(self, series: str, entries: list[Entry], warnings: list[str],
                       metadata: dict = None) -> list[Entry]:
        print(f"\n{series}: {len(entries)} folders")
        for entry in entries:
            self.print_entry(entry)
        self.print_metadata(series, metadata)
        self.print_warnings(warnings)

        while True:
            response = input("Rename all? [Y]es / [r]eview each / [n]o: ").strip().lower()
            if response in ('', 'y', 'yes'):
                return entries
            if response in ('r', 'review'):
                return self.confirm_each(entries, [])
            if response in ('n', 'no'):
                print(f"Not renamed: {series}")
                return []

    def confirm_each(self, entries: list[Entry], warnings: list[str], metadata: dict = None) -> list[Entry]:
        approved = []
        for entry in entries:
            print()
            self.print_entry(entry)
            self.print_metadata(entry.series, metadata)
            self.print_warnings(warnings)
            response = input("Rename? [Y/n]: ").strip().lower()
            if response in ('', 'y', 'yes'):
                approved.append(entry)
            else:
                print(f"Not renamed: '{entry.original}'")
        return approved

    def confirm_metadata(self, series: str, metadata: dict) -> bool:
        print(f"\n{series}: folders already have the right name")
        self.print_metadata(series, metadata)
        response = input("Save metadata? [Y/n]: ").strip().lower()
        if response in ('', 'y', 'yes'):
            return True
        print(f"Metadata not saved: {series}")
        return False

    def is_cached(self, series: str) -> bool:
        cached = self.metadata_cache.get(series)
        return cached is not None and same_country(cached.get('country'), self.country)

    @staticmethod
    def print_entry(entry: Entry):
        print(f"  '{entry.original}' -> '{entry.new_name}'")
        if entry.changes:
            print(f"      changed: {'; '.join(entry.changes)}")
        if entry.notes:
            print(f"      note: {entry.notes}")

    def print_metadata(self, series: str, metadata: dict | None):
        if not metadata:
            return
        edition = ', '.join(filter(None, [self.country, metadata.get('language_iso')]))
        print(f"  metadata{f' ({edition})' if edition else ''}:")
        for name in SERIES_FIELDS:
            print(f"      {name}: {metadata.get(name) or '-'}")
        if metadata.get('notes'):
            print(f"      note: {metadata['notes']}")
        cached = self.metadata_cache.get(series)
        if cached is not None:
            print(f"      replaces the saved metadata for country: {cached.get('country') or 'none'}")

    @staticmethod
    def print_warnings(warnings: list[str]):
        for warning in warnings:
            print(f"  Warning: {warning}")


def same_country(first: str | None, second: str | None) -> bool:
    return (first or '').strip().casefold() == (second or '').strip().casefold()
