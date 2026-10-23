import json
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from browser_agent.config import settings
from browser_agent.models import HistoryItem, PlanResponse


def _connect() -> sqlite3.Connection:
    root = Path(settings.data_dir)
    root.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(root / "browser-agent.db", timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with closing(_connect()) as connection, connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                goal TEXT NOT NULL,
                start_url TEXT NOT NULL,
                allowed_domains TEXT NOT NULL,
                status TEXT NOT NULL,
                snapshot TEXT NOT NULL,
                plan TEXT NOT NULL,
                execution TEXT NOT NULL,
                created_at TEXT NOT NULL
            )"""
        )
        connection.execute("CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at DESC)")


def save_run(run: PlanResponse) -> None:
    with closing(_connect()) as connection, connection:
        connection.execute(
            """INSERT INTO runs(
                run_id, goal, start_url, allowed_domains, status, snapshot, plan, execution, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                run.run_id,
                run.goal,
                run.start_url,
                json.dumps(run.allowed_domains),
                run.status,
                run.snapshot.model_dump_json(),
                run.plan.model_dump_json(),
                json.dumps(run.execution),
                run.created_at.astimezone(UTC).isoformat(),
            ),
        )


def get_run(run_id: str) -> PlanResponse | None:
    with closing(_connect()) as connection, connection:
        row = connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    if row is None:
        return None
    return PlanResponse(
        run_id=row["run_id"],
        goal=row["goal"],
        start_url=row["start_url"],
        allowed_domains=json.loads(row["allowed_domains"]),
        status=row["status"],
        snapshot=json.loads(row["snapshot"]),
        plan=json.loads(row["plan"]),
        execution=json.loads(row["execution"]),
        created_at=datetime.fromisoformat(row["created_at"]),
    )


def claim_run(run_id: str) -> bool:
    with closing(_connect()) as connection, connection:
        cursor = connection.execute(
            "UPDATE runs SET status = 'running' WHERE run_id = ? AND status = 'planned'",
            (run_id,),
        )
        return cursor.rowcount == 1


def update_run(run: PlanResponse) -> None:
    with closing(_connect()) as connection, connection:
        connection.execute(
            "UPDATE runs SET status = ?, execution = ? WHERE run_id = ?",
            (run.status, json.dumps(run.execution), run.run_id),
        )


def list_runs(limit: int = 20) -> list[HistoryItem]:
    with closing(_connect()) as connection, connection:
        rows = connection.execute(
            "SELECT run_id, goal, start_url, status, created_at FROM runs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [
        HistoryItem(
            run_id=row["run_id"],
            goal=row["goal"],
            start_url=row["start_url"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )
        for row in rows
    ]
