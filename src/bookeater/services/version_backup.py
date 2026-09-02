from __future__ import annotations

"""Pre-migration backup guard for application-version transitions.

The version marker is deliberately stored beside, not inside, the SQLite database. That lets
BookEater decide whether a backup is needed before constructing stores that may run schema
migrations. Live databases are copied with SQLite's backup API so WAL state is captured safely.
"""

from datetime import datetime
from pathlib import Path
import re
import sqlite3

VERSION_MARKER = 'last_successful_app_version.txt'
DEFAULT_VERSION_BACKUP_RETENTION = 5
_SAFE = re.compile(r'[^0-9A-Za-z._-]+')


class VersionBackupError(RuntimeError):
    pass


def _slug(value: str) -> str:
    text = _SAFE.sub('-', str(value or 'unknown').strip()).strip('-')
    return text[:48] or 'unknown'


def _marker_path(data_dir: str | Path) -> Path:
    return Path(data_dir) / VERSION_MARKER


def read_last_successful_version(data_dir: str | Path) -> str | None:
    marker = _marker_path(data_dir)
    if not marker.is_file():
        return None
    try:
        value = marker.read_text(encoding='utf-8').strip()
    except (OSError, UnicodeDecodeError):
        return None
    return value or None


def mark_version_success(data_dir: str | Path, version: str) -> None:
    marker = _marker_path(data_dir)
    marker.parent.mkdir(parents=True, exist_ok=True)
    temp = marker.with_name(marker.name + '.tmp')
    temp.write_text(str(version).strip() + '\n', encoding='utf-8')
    temp.replace(marker)


def _backup_folder(data_dir: str | Path) -> Path:
    return Path(data_dir) / 'backups' / 'version-upgrades'


def prune_version_backups(
    data_dir: str | Path,
    *,
    keep: int = DEFAULT_VERSION_BACKUP_RETENTION,
) -> list[Path]:
    """Best-effort retention for automatic *version-upgrade* SQLite snapshots only.

    Portable ``.bookeater-seed`` backups and unrelated files are deliberately outside this scope.
    Failure to delete an old automatic snapshot is harmless and must never block app startup.
    """
    keep = max(1, int(keep))
    folder = _backup_folder(data_dir)
    if not folder.is_dir():
        return []
    try:
        candidates = sorted(
            (p for p in folder.glob('*.sqlite3') if p.is_file()),
            key=lambda p: (p.stat().st_mtime_ns, p.name),
        )
    except OSError:
        return []
    excess = candidates[:-keep]
    removed: list[Path] = []
    for path in excess:
        try:
            path.unlink()
            removed.append(path)
        except OSError:
            continue
    return removed


def _backup_destination(data_dir: Path, previous: str | None, current: str) -> Path:
    folder = _backup_folder(data_dir)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    stem = f'pre-version-{_slug(previous or "unknown")}-to-{_slug(current)}-{stamp}'
    candidate = folder / f'{stem}.sqlite3'
    suffix = 1
    while candidate.exists():
        candidate = folder / f'{stem}-{suffix}.sqlite3'
        suffix += 1
    return candidate


def backup_live_database(source: str | Path, destination: str | Path) -> Path:
    source = Path(source)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_name(destination.name + '.tmp')
    temp.unlink(missing_ok=True)
    try:
        src = sqlite3.connect(str(source), timeout=5.0)
        dst = sqlite3.connect(str(temp), timeout=5.0)
        try:
            src.execute('PRAGMA busy_timeout=5000')
            dst.execute('PRAGMA busy_timeout=5000')
            src.backup(dst)
            dst.commit()
            check = dst.execute('PRAGMA quick_check').fetchone()
            if not check or str(check[0]).lower() != 'ok':
                raise VersionBackupError('version backup failed SQLite quick_check')
        finally:
            dst.close()
            src.close()
        temp.replace(destination)
        return destination
    except Exception as exc:
        temp.unlink(missing_ok=True)
        if isinstance(exc, VersionBackupError):
            raise
        raise VersionBackupError('could not create pre-version SQLite backup') from exc


def prepare_version_transition(
    *,
    data_dir: str | Path,
    database_path: str | Path,
    current_version: str,
) -> Path | None:
    data = Path(data_dir)
    db = Path(database_path)
    previous = read_last_successful_version(data)
    if not db.is_file() or previous == current_version:
        return None
    destination = _backup_destination(data, previous, current_version)
    created = backup_live_database(db, destination)
    # Retention is intentionally best-effort and runs only after a verified new snapshot exists.
    prune_version_backups(data)
    return created
