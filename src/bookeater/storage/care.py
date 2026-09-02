from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class CareState:
    fullness: int
    mood: int
    cleanliness: int
    bond: int


_ACTIONS = {
    'snack': (18, 3, 0, 1),
    'play': (0, 18, 0, 2),
    'wash': (0, 2, 22, 1),
    'minigame': (0, 20, 0, 3),
}


class MonsterCareStore:
    """Optional pet-care state that never participates in reading evolution."""

    def __init__(self, path: str | Path):
        self.path = str(path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=5.0)
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA busy_timeout=5000')
        if self.path != ':memory:':
            con.execute('PRAGMA journal_mode=WAL')
        return con

    def _init_db(self) -> None:
        con = self._connect()
        try:
            con.executescript(
                """
                CREATE TABLE IF NOT EXISTS monster_care (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    fullness INTEGER NOT NULL DEFAULT 65,
                    mood INTEGER NOT NULL DEFAULT 65,
                    cleanliness INTEGER NOT NULL DEFAULT 75,
                    bond INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                INSERT OR IGNORE INTO monster_care(singleton) VALUES(1);
                """
            )
            con.commit()
        finally:
            con.close()

    @staticmethod
    def _clamp(value: int) -> int:
        return max(0, min(100, int(value)))

    def load(self) -> CareState:
        con = self._connect()
        try:
            row = con.execute(
                'SELECT fullness,mood,cleanliness,bond FROM monster_care WHERE singleton=1'
            ).fetchone()
            if row is None:
                raise RuntimeError('monster_care singleton missing')
            return CareState(
                self._clamp(row['fullness']), self._clamp(row['mood']),
                self._clamp(row['cleanliness']), self._clamp(row['bond']),
            )
        finally:
            con.close()

    def apply(self, action: str) -> CareState:
        action = str(action)
        if action not in _ACTIONS:
            raise ValueError(f'unknown care action: {action}')
        current = self.load()
        df, dm, dc, db = _ACTIONS[action]
        next_state = CareState(
            self._clamp(current.fullness + df),
            self._clamp(current.mood + dm),
            self._clamp(current.cleanliness + dc),
            self._clamp(current.bond + db),
        )
        con = self._connect()
        try:
            con.execute(
                """
                UPDATE monster_care
                SET fullness=?,mood=?,cleanliness=?,bond=?,updated_at=CURRENT_TIMESTAMP
                WHERE singleton=1
                """,
                (next_state.fullness, next_state.mood, next_state.cleanliness, next_state.bond),
            )
            con.commit()
        finally:
            con.close()
        return next_state
