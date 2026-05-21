"""Task queue with SQLite persistence."""

import json
import sqlite3
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional


class TaskManager:
    """Manages task queue with SQLite storage."""

    def __init__(self, db_path: str = "browserbot.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    headless INTEGER DEFAULT 1,
                    max_steps INTEGER DEFAULT 30,
                    session_id TEXT,
                    result TEXT,
                    error TEXT,
                    steps INTEGER DEFAULT 0,
                    screenshots TEXT DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    completed_at TEXT
                )
            """)
            conn.commit()
            conn.close()

    def create_task(self, goal: str, headless: bool = True, max_steps: int = 30,
                    session_id: Optional[str] = None) -> dict:
        """Create a new task and return its info."""
        task_id = str(uuid.uuid4())[:8]
        now = datetime.utcnow().isoformat()

        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute(
                """INSERT INTO tasks (id, goal, status, headless, max_steps, session_id, created_at)
                   VALUES (?, ?, 'pending', ?, ?, ?, ?)""",
                (task_id, goal, int(headless), max_steps, session_id or "", now),
            )
            conn.commit()
            conn.close()

        return {
            "id": task_id,
            "goal": goal,
            "status": "pending",
            "created_at": now,
        }

    def get_task(self, task_id: str) -> Optional[dict]:
        """Get a task by ID."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
            conn.close()

        if row is None:
            return None

        task = dict(row)
        task["headless"] = bool(task["headless"])
        task["screenshots"] = json.loads(task.get("screenshots", "[]"))
        if task.get("result"):
            try:
                task["result"] = json.loads(task["result"])
            except (json.JSONDecodeError, TypeError):
                pass
        return task

    def list_tasks(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """List tasks with pagination."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            ).fetchall()
            conn.close()

        tasks = []
        for row in rows:
            task = dict(row)
            task["headless"] = bool(task["headless"])
            tasks.append(task)
        return tasks

    def update_task(self, task_id: str, **kwargs) -> bool:
        """Update a task's fields."""
        allowed = {"status", "result", "error", "steps", "screenshots", "completed_at"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}

        if not updates:
            return False

        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [task_id]

        with self._lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)
            conn.commit()
            conn.close()
        return True

    def mark_running(self, task_id: str):
        """Mark a task as running."""
        self.update_task(task_id, status="running")

    def mark_completed(self, task_id: str, result, steps: int, screenshots: list[str] = None):
        """Mark a task as completed."""
        now = datetime.utcnow().isoformat()
        self.update_task(
            task_id,
            status="completed",
            result=json.dumps(result) if not isinstance(result, str) else result,
            steps=steps,
            screenshots=json.dumps(screenshots or []),
            completed_at=now,
        )

    def mark_failed(self, task_id: str, error: str, steps: int = 0):
        """Mark a task as failed."""
        now = datetime.utcnow().isoformat()
        self.update_task(
            task_id,
            status="failed",
            error=str(error),
            steps=steps,
            completed_at=now,
        )

    def get_total_count(self) -> int:
        """Get total number of tasks."""
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
            conn.close()
        return count
