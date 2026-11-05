from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .schemas import ColonyResult, Event, TaskResponse, TaskStatus


def now() -> datetime:
    return datetime.now(timezone.utc)


class Repository:
    def __init__(self, database_url: str = "komorebi.db") -> None:
        self.path = Path(database_url)
        self._initialize()

    def _connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connection() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY, description TEXT NOT NULL, language TEXT NOT NULL,
                    status TEXT NOT NULL, created_at TEXT NOT NULL, winner_id TEXT
                );
                CREATE TABLE IF NOT EXISTS colonies (
                    id TEXT PRIMARY KEY, task_id TEXT NOT NULL, strategy TEXT NOT NULL,
                    status TEXT NOT NULL, result_json TEXT, FOREIGN KEY(task_id) REFERENCES tasks(id)
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, task_id TEXT NOT NULL,
                    event_json TEXT NOT NULL, FOREIGN KEY(task_id) REFERENCES tasks(id)
                );
                """
            )

    def create_task(self, task: TaskResponse) -> None:
        with self._connection() as db:
            db.execute(
                "INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?)",
                (task.id, task.description, task.language, task.status.value, task.created_at.isoformat(), None),
            )

    def update_task(self, task_id: str, status: TaskStatus, winner_id: str | None = None) -> None:
        with self._connection() as db:
            db.execute("UPDATE tasks SET status=?, winner_id=COALESCE(?, winner_id) WHERE id=?", (status.value, winner_id, task_id))

    def get_task(self, task_id: str) -> TaskResponse | None:
        with self._connection() as db:
            row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return TaskResponse.model_validate(dict(row)) if row else None

    def upsert_colony(self, result: ColonyResult, task_id: str) -> None:
        with self._connection() as db:
            db.execute(
                "INSERT OR REPLACE INTO colonies VALUES (?, ?, ?, ?, ?)",
                (result.id, task_id, result.strategy.value, result.status.value, result.model_dump_json()),
            )

    def colonies(self, task_id: str) -> list[ColonyResult]:
        with self._connection() as db:
            rows = db.execute("SELECT result_json FROM colonies WHERE task_id=?", (task_id,)).fetchall()
        return [ColonyResult.model_validate_json(row["result_json"]) for row in rows if row["result_json"]]

    def append_event(self, event: Event) -> None:
        with self._connection() as db:
            db.execute("INSERT INTO events (task_id, event_json) VALUES (?, ?)", (event.task_id, event.model_dump_json()))

    def events(self, task_id: str) -> list[dict[str, Any]]:
        with self._connection() as db:
            rows = db.execute("SELECT event_json FROM events WHERE task_id=? ORDER BY id", (task_id,)).fetchall()
        return [json.loads(row["event_json"]) for row in rows]
