from __future__ import annotations

"""Durable player-facing dates for the current monster.

`met_at` is the date this local monster profile began.  On migration from an older build we use
the earliest existing reading entry as the best available historical approximation instead of
pretending the update date was the first meeting.  `first_fed_at` is derived from the earliest
successfully consumed reading record and therefore remains stable without duplicating feed data.
"""

from dataclasses import dataclass
from pathlib import Path
import sqlite3


@dataclass(frozen=True)
class MonsterMilestones:
    met_at: str
    first_fed_at: str | None


class MonsterMilestoneStore:
    def __init__(self, path: str | Path):
        self.path = str(path)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self.path, timeout=5.0)
        con.row_factory = sqlite3.Row
        con.execute('PRAGMA foreign_keys=ON')
        con.execute('PRAGMA busy_timeout=5000')
        if self.path != ':memory:':
            con.execute('PRAGMA journal_mode=WAL')
        return con

    def _init_db(self) -> None:
        con = self._connect()
        try:
            # SQLiteGameStore creates reading_entries before this store is bootstrapped.
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS monster_milestones (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    met_at TEXT NOT NULL
                )
                """
            )
            con.execute(
                """
                INSERT OR IGNORE INTO monster_milestones(singleton, met_at)
                VALUES(
                    1,
                    COALESCE(
                        (SELECT MIN(created_at) FROM reading_entries),
                        CURRENT_TIMESTAMP
                    )
                )
                """
            )
            con.commit()
        finally:
            con.close()

    def load(self) -> MonsterMilestones:
        con = self._connect()
        try:
            row = con.execute(
                'SELECT met_at FROM monster_milestones WHERE singleton=1'
            ).fetchone()
            if row is None:
                raise RuntimeError('monster milestone singleton is missing')
            first = con.execute(
                "SELECT MIN(fed_at) AS first_fed_at FROM reading_entries "
                "WHERE status='fed' AND fed_at IS NOT NULL"
            ).fetchone()
            return MonsterMilestones(
                met_at=str(row['met_at']),
                first_fed_at=(str(first['first_fed_at']) if first and first['first_fed_at'] else None),
            )
        finally:
            con.close()
