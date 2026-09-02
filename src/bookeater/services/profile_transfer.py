from __future__ import annotations

"""Safety envelope around portable profile transfer operations.

The core seed serializer stays format-focused. Desktop/destructive callers use this module so they
cannot accidentally overwrite the live SQLite file and so a planted profile always moves the live
revision forward. A monotonically increasing revision prevents a stale analysis task that started
before planting from later committing against the transplanted profile.
"""

from pathlib import Path
import sqlite3

from .data_transfer import SeedSummary, export_seed, import_seed, reset_reading_and_genetics


class UnsafeTransferTarget(ValueError):
    pass


def _same_path(left: str | Path, right: str | Path) -> bool:
    try:
        return Path(left).expanduser().resolve() == Path(right).expanduser().resolve()
    except (OSError, RuntimeError):
        return Path(left).absolute() == Path(right).absolute()


def _install_monotonic_revision_guard(database_path: str | Path) -> None:
    con = sqlite3.connect(str(database_path), timeout=5.0)
    con.execute('PRAGMA busy_timeout=5000')
    try:
        # recursive_triggers defaults OFF for this connection. The inner update therefore does not
        # recursively fire itself; normal growth updates already increment revision and skip WHEN.
        con.execute(
            """
            CREATE TRIGGER IF NOT EXISTS trg_bookeater_monotonic_revision
            AFTER UPDATE OF revision ON monster_state
            FOR EACH ROW
            WHEN NEW.revision <= OLD.revision
            BEGIN
                UPDATE monster_state
                SET revision = OLD.revision + 1
                WHERE singleton = NEW.singleton;
            END
            """
        )
        con.commit()
    finally:
        con.close()


def export_profile_seed(database_path: str | Path, destination: str | Path) -> SeedSummary:
    if str(database_path) != ':memory:' and _same_path(database_path, destination):
        raise UnsafeTransferTarget('the live database cannot be used as a seed destination')
    return export_seed(database_path, destination)


def plant_profile_seed(
    database_path: str | Path,
    seed_path: str | Path,
    *,
    data_dir: str | Path,
) -> tuple[SeedSummary, Path]:
    if str(database_path) != ':memory:' and _same_path(database_path, seed_path):
        raise UnsafeTransferTarget('the live database is not a seed file')
    _install_monotonic_revision_guard(database_path)
    return import_seed(database_path, seed_path, data_dir=data_dir)


def reset_profile(database_path: str | Path, *, data_dir: str | Path) -> Path:
    _install_monotonic_revision_guard(database_path)
    return reset_reading_and_genetics(database_path, data_dir=data_dir)
