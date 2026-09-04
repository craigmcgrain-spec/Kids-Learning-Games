from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from PySide6.QtCore import QStandardPaths


@dataclass(frozen=True, slots=True)
class Profile:
    id: int
    name: str
    icon: str
    total_points: int
    daily_points: int


class LearningStore:
    def __init__(self, database_path: Path | None = None) -> None:
        if database_path is None:
            data_dir = Path(
                QStandardPaths.writableLocation(
                    QStandardPaths.StandardLocation.AppLocalDataLocation
                )
            )
            data_dir.mkdir(parents=True, exist_ok=True)
            database_path = data_dir / "learning.db"
        self.connection = sqlite3.connect(database_path)
        self.connection.row_factory = sqlite3.Row
        self._create_schema()

    def _create_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL COLLATE NOCASE UNIQUE,
                icon TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS score_events (
                id INTEGER PRIMARY KEY,
                profile_id INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
                points INTEGER NOT NULL CHECK(points > 0),
                scored_on TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS score_events_profile_date
                ON score_events(profile_id, scored_on);
            """
        )
        self.connection.commit()

    def profiles(self, today: date | None = None) -> list[Profile]:
        score_date = (today or date.today()).isoformat()
        rows = self.connection.execute(
            """
            SELECT p.id, p.name, p.icon,
                   COALESCE(SUM(s.points), 0) AS total_points,
                   COALESCE(SUM(CASE WHEN s.scored_on = ? THEN s.points ELSE 0 END), 0)
                       AS daily_points
            FROM profiles p
            LEFT JOIN score_events s ON s.profile_id = p.id
            GROUP BY p.id
            ORDER BY p.name COLLATE NOCASE
            """,
            (score_date,),
        ).fetchall()
        return [Profile(**dict(row)) for row in rows]

    def add_profile(self, name: str, icon: str) -> Profile:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Please enter a name.")
        if len(clean_name) > 24:
            raise ValueError("Names can be up to 24 characters.")
        try:
            cursor = self.connection.execute(
                "INSERT INTO profiles(name, icon) VALUES (?, ?)",
                (clean_name, icon),
            )
            self.connection.commit()
        except sqlite3.IntegrityError as error:
            raise ValueError("That name is already being used.") from error
        return Profile(cursor.lastrowid, clean_name, icon, 0, 0)

    def add_point(self, profile_id: int, today: date | None = None) -> None:
        self.connection.execute(
            "INSERT INTO score_events(profile_id, points, scored_on) VALUES (?, 1, ?)",
            (profile_id, (today or date.today()).isoformat()),
        )
        self.connection.commit()

    def profile(self, profile_id: int, today: date | None = None) -> Profile:
        for profile in self.profiles(today):
            if profile.id == profile_id:
                return profile
        raise LookupError(f"Profile {profile_id} does not exist")

    def close(self) -> None:
        self.connection.close()

