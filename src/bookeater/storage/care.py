from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
import sqlite3
from typing import Callable


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

    DAILY_BOND_GAIN_LIMIT = 5
    DAILY_NEGLECT_LOSS = 2

    def __init__(self, path: str | Path, *, today: Callable[[], date] | None = None):
        self.path = str(path)
        self._today = today or (lambda: date.today())
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
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    bond_gain_date TEXT NOT NULL DEFAULT '',
                    bond_gain_today INTEGER NOT NULL DEFAULT 0,
                    last_cared_date TEXT NOT NULL DEFAULT '',
                    last_decay_date TEXT NOT NULL DEFAULT ''
                );
                INSERT OR IGNORE INTO monster_care(singleton) VALUES(1);
                """
            )
            columns = {str(row['name']) for row in con.execute('PRAGMA table_info(monster_care)')}
            additions = {
                'bond_gain_date': "TEXT NOT NULL DEFAULT ''",
                'bond_gain_today': 'INTEGER NOT NULL DEFAULT 0',
                'last_cared_date': "TEXT NOT NULL DEFAULT ''",
                'last_decay_date': "TEXT NOT NULL DEFAULT ''",
            }
            for name, declaration in additions.items():
                if name not in columns:
                    con.execute(f'ALTER TABLE monster_care ADD COLUMN {name} {declaration}')
            today = self._today().isoformat()
            con.execute(
                """
                UPDATE monster_care
                SET bond_gain_date=CASE WHEN bond_gain_date='' THEN ? ELSE bond_gain_date END,
                    last_cared_date=CASE WHEN last_cared_date='' THEN ? ELSE last_cared_date END,
                    last_decay_date=CASE WHEN last_decay_date='' THEN ? ELSE last_decay_date END
                WHERE singleton=1
                """,
                (today, today, today),
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
            self._apply_neglect_decay(con)
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

    def _apply_neglect_decay(self, con: sqlite3.Connection) -> None:
        row = con.execute(
            'SELECT bond,last_cared_date,last_decay_date FROM monster_care WHERE singleton=1'
        ).fetchone()
        if row is None:
            return
        today = self._today()
        try:
            cared = date.fromisoformat(str(row['last_cared_date']))
            last_decay = date.fromisoformat(str(row['last_decay_date']))
        except ValueError:
            cared = last_decay = today
        # The day after care is a grace day. Each fully missed day after that costs at most 2.
        decay_through = today - timedelta(days=1)
        baseline = max(cared, last_decay)
        missed_days = max(0, (decay_through - baseline).days)
        if missed_days <= 0:
            return
        next_bond = self._clamp(int(row['bond']) - missed_days * self.DAILY_NEGLECT_LOSS)
        con.execute(
            'UPDATE monster_care SET bond=?,last_decay_date=?,updated_at=CURRENT_TIMESTAMP WHERE singleton=1',
            (next_bond, decay_through.isoformat()),
        )
        con.commit()

    def apply(self, action: str) -> CareState:
        action = str(action)
        if action not in _ACTIONS:
            raise ValueError(f'unknown care action: {action}')
        current = self.load()
        df, dm, dc, db = _ACTIONS[action]
        today = self._today().isoformat()
        con = self._connect()
        try:
            row = con.execute(
                'SELECT bond_gain_date,bond_gain_today FROM monster_care WHERE singleton=1'
            ).fetchone()
            gained = int(row['bond_gain_today']) if row and row['bond_gain_date'] == today else 0
            allowed_bond = min(db, max(0, self.DAILY_BOND_GAIN_LIMIT - gained))
            next_state = CareState(
                self._clamp(current.fullness + df),
                self._clamp(current.mood + dm),
                self._clamp(current.cleanliness + dc),
                self._clamp(current.bond + allowed_bond),
            )
            con.execute(
                """
                UPDATE monster_care
                SET fullness=?,mood=?,cleanliness=?,bond=?,updated_at=CURRENT_TIMESTAMP,
                    bond_gain_date=?,bond_gain_today=?,last_cared_date=?
                WHERE singleton=1
                """,
                (
                    next_state.fullness, next_state.mood, next_state.cleanliness, next_state.bond,
                    today, gained + allowed_bond, today,
                ),
            )
            con.commit()
        finally:
            con.close()
        return next_state
