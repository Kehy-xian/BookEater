from __future__ import annotations

"""Desktop runtime bootstrap for the local-first BookEater app.

Startup must not depend on ONNX/model availability: the SQLite store is opened first and the
semantic model is loaded lazily only when a note is actually analyzed. If model loading fails,
ReadingFeedService's save-first contract leaves the note safely pending for retry.
"""

from dataclasses import dataclass
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any

from .game.loop import ReadingFeedService
from .storage.sqlite_store import SQLiteGameStore

APP_DIR_NAME = 'BookEater'
DB_FILENAME = 'bookeater.sqlite3'
MODEL_RELATIVE_PATH = Path('resources/models/multilingual-e5-small-onnx')


class RuntimeStartupError(RuntimeError):
    """Local app data cannot be opened safely."""


class ModelUnavailable(RuntimeError):
    """Bundled local semantic model is missing, corrupt, or failed to initialize."""


def default_data_dir(*, platform: str | None = None, environ: dict[str,str] | None = None, home: Path | None = None) -> Path:
    platform = platform or sys.platform
    env = dict(os.environ if environ is None else environ)
    home = Path.home() if home is None else Path(home)

    override = env.get('BOOKEATER_DATA_DIR')
    if override:
        return Path(override).expanduser()

    if platform.startswith('win'):
        base = env.get('LOCALAPPDATA') or env.get('APPDATA')
        return (Path(base).expanduser() if base else home / 'AppData' / 'Local') / APP_DIR_NAME
    if platform == 'darwin':
        return home / 'Library' / 'Application Support' / APP_DIR_NAME
    xdg = env.get('XDG_DATA_HOME')
    return (Path(xdg).expanduser() if xdg else home / '.local' / 'share') / 'bookeater'


def resource_root(*, environ: dict[str,str] | None = None) -> Path:
    env = dict(os.environ if environ is None else environ)
    override = env.get('BOOKEATER_RESOURCE_ROOT')
    if override:
        return Path(override).expanduser()
    # PyInstaller extracts one-file resources under _MEIPASS. Avoid importing PyInstaller.
    bundle = getattr(sys, '_MEIPASS', None)
    if bundle:
        return Path(bundle)
    # src/bookeater/runtime.py -> repository/package root is two parents above src/bookeater.
    return Path(__file__).resolve().parents[2]


class LazyLocalAnalyzer:
    """Load the ONNX E5 classifier on first use, never during app startup."""

    def __init__(self, model_dir: str | Path):
        self.model_dir = Path(model_dir)
        self._classifier: Any | None = None
        self._failure: Exception | None = None

    @property
    def loaded(self) -> bool:
        return self._classifier is not None

    def _load(self):
        if self._classifier is not None:
            return self._classifier
        if self._failure is not None:
            raise ModelUnavailable('local semantic model is unavailable') from self._failure
        try:
            required = (self.model_dir / 'model.onnx', self.model_dir / 'tokenizer.json')
            missing = [p.name for p in required if not p.is_file()]
            if missing:
                raise FileNotFoundError(', '.join(missing))
            # Heavy optional dependencies are imported here so the UI can still start, save a
            # note and present a recoverable pending state if packaging/model setup is broken.
            from .nlp.hybrid_classifier_v31 import HybridE5ClassifierV31
            self._classifier = HybridE5ClassifierV31(self.model_dir)
            return self._classifier
        except Exception as exc:
            self._failure = exc
            raise ModelUnavailable('local semantic model is unavailable') from exc

    def analyze(self, text: str):
        return self._load().analyze(text)

    def reset_failure(self) -> None:
        """Allow an explicit retry after resources have been repaired/reinstalled."""
        self._failure = None


@dataclass(frozen=True)
class BookEaterRuntime:
    data_dir: Path
    database_path: Path
    model_dir: Path
    store: SQLiteGameStore
    analyzer: LazyLocalAnalyzer
    feed_service: ReadingFeedService


def bootstrap_runtime(
    *,
    data_dir: str | Path | None = None,
    resources: str | Path | None = None,
) -> BookEaterRuntime:
    data = Path(data_dir) if data_dir is not None else default_data_dir()
    root = Path(resources) if resources is not None else resource_root()
    db_path = data / DB_FILENAME
    model_dir = root / MODEL_RELATIVE_PATH

    try:
        data.mkdir(parents=True, exist_ok=True)
        if not data.is_dir():
            raise OSError('data path is not a directory')
        # A tiny create/delete probe catches common installer/permissions failures before SQLite
        # produces a less actionable error. Existing user data is never modified by this probe.
        probe = data / '.write-test'
        with probe.open('w', encoding='utf-8') as f:
            f.write('ok')
        probe.unlink(missing_ok=True)
        store = SQLiteGameStore(db_path)
    except (OSError, sqlite3.DatabaseError) as exc:
        raise RuntimeStartupError('local BookEater data could not be opened safely') from exc

    analyzer = LazyLocalAnalyzer(model_dir)
    service = ReadingFeedService(store, analyzer)
    return BookEaterRuntime(data, db_path, model_dir, store, analyzer, service)
