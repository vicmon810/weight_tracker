from contextlib import closing
from datetime import date as Date
from datetime import datetime, timezone
import os
import sqlite3

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, model_validator


class DailyHealthRequest(BaseModel):
    date: Date
    weight_kg: float | None = Field(default=None, gt=0)
    steps: int | None = Field(default=None, ge=0)
    sleep_hours: float | None = Field(default=None, ge=0, le=24)

    @model_validator(mode="after")
    def require_metric(self):
        if (
            self.weight_kg is None
            and self.steps is None
            and self.sleep_hours is None
        ):
            raise ValueError("at least one health metric is required")
        return self


def create_app(db_path: str) -> FastAPI:
    app = FastAPI(title="HealthPi API")

    def connect() -> sqlite3.Connection:
        connection = sqlite3.connect(db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    with closing(connect()) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS daily_health (
                date TEXT PRIMARY KEY,
                weight_kg REAL CHECK (weight_kg > 0),
                steps INTEGER CHECK (steps >= 0),
                sleep_hours REAL CHECK (
                    sleep_hours >= 0 AND sleep_hours <= 24
                ),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.commit()

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/daily-health")
    def upsert_daily_health(entry: DailyHealthRequest):
        now = datetime.now(timezone.utc).isoformat()
        with closing(connect()) as connection:
            connection.execute(
                """
                INSERT INTO daily_health (
                    date,
                    weight_kg,
                    steps,
                    sleep_hours,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    weight_kg = COALESCE(
                        excluded.weight_kg,
                        daily_health.weight_kg
                    ),
                    steps = COALESCE(
                        excluded.steps,
                        daily_health.steps
                    ),
                    sleep_hours = COALESCE(
                        excluded.sleep_hours,
                        daily_health.sleep_hours
                    ),
                    updated_at = excluded.updated_at
                """,
                (
                    entry.date.isoformat(),
                    entry.weight_kg,
                    entry.steps,
                    entry.sleep_hours,
                    now,
                    now,
                ),
            )
            connection.commit()
        return {"status": "ok", "date": entry.date.isoformat()}

    @app.get("/daily-health/{entry_date}")
    def get_daily_health(entry_date: Date):
        with closing(connect()) as connection:
            row = connection.execute(
                "SELECT * FROM daily_health WHERE date = ?",
                (entry_date.isoformat(),),
            ).fetchone()
        if row is None:
            raise HTTPException(
                status_code=404,
                detail="daily health not found",
            )
        return dict(row)

    return app


app = create_app(os.environ.get("HEALTH_DB_PATH", "health.db"))
