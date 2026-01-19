from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
from datetime import datetime

app = FastAPI(title="Health Tracker API")

DB_PATH = "health.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
    PRAGMA foreign_keys = ON;

    -- Observation core: immutable facts
    -- Identity rule:
    --   PK = (device_id, minute_bucket, body_mass_01, steps, sleep_minutes)
    CREATE TABLE IF NOT EXISTS observation_core (
    device_id      TEXT NOT NULL,            -- stable device identifier (e.g., UUID string)
    observed_at    TEXT NOT NULL,            -- ISO8601 timestamp when observation happened (raw fact time)
    minute_bucket  INTEGER NOT NULL,         -- floor(epoch_seconds/60)
    body_mass_01   REAL NOT NULL,            -- rounded to 0.1 kg
    steps          INTEGER NOT NULL,
    sleep_minutes  INTEGER NOT NULL,

    -- Composite primary key = your "ob + temporal" identity
    PRIMARY KEY (device_id, minute_bucket, body_mass_01, steps, sleep_minutes),

    -- Basic sanity constraints (optional but helpful)
    CHECK (steps >= 0),
    CHECK (sleep_minutes >= 0)
    );

    -- Provenance: who/what produced the observation, plus audit metadata
    -- It references the exact observation identity (same composite key).
    CREATE TABLE IF NOT EXISTS observation_provenance (
    device_id      TEXT NOT NULL,
    minute_bucket  INTEGER NOT NULL,
    body_mass_01   REAL NOT NULL,
    steps          INTEGER NOT NULL,
    sleep_minutes  INTEGER NOT NULL,

    app_version    TEXT,
    source_kind    TEXT NOT NULL DEFAULT 'unknown',  -- 'healthkit', 'manual', 'import'
    ingested_at    TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
    provenance_json TEXT,                             -- optional structured provenance

    PRIMARY KEY (device_id, minute_bucket, body_mass_01, steps, sleep_minutes),

    FOREIGN KEY (device_id, minute_bucket, body_mass_01, steps, sleep_minutes)
        REFERENCES observation_core (device_id, minute_bucket, body_mass_01, steps, sleep_minutes)
        ON DELETE CASCADE
    );

    -- Helpful indexes for time-based queries (not identity)
    CREATE INDEX IF NOT EXISTS idx_observation_core_observed_at
    ON observation_core (observed_at);

    CREATE INDEX IF NOT EXISTS idx_observation_core_device_time
    ON observation_core (device_id, minute_bucket);
    """)
    conn.commit()
    conn.close()


init_db()


class WeightEntry(BaseModel):
    weight: float
    note: str | None = None


class DailyCheckin(BaseModel):
    checkin_date:str | None = None
    mood: str
    diet_note: str
    exercise_minutes: int | None = None
    exercise_note: str | None = None
    sleep_hours: float | None = None
    weight: float | None = None
    raw_text: str | None = None
    stress_score: float | None = None 
    sentiment: str | None = None

@app.post("/weigh_in")
async def add_weight(entry: WeightEntry):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO weigh_in (weight, note, timestamp) VALUES (?, ?, ?)",
        (entry.weight, entry.note, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return {"status": "ok", "weight": entry.weight}


@app.get("/weigh_in")
async def list_weights():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT * FROM weigh_in ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return rows

@app.post("/checkin")
async def add_checkin(entry: DailyCheckin):

    target_date = entry.checkin_date 
    if target_date is None:
        target_date = datetime.now().isoformat()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO daily_checkin (
            checkin_date, mood, diet_note, exercise_minutes, 
            exercise_note, sleep_hours, weight
        ) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(checkin_date) 
        DO UPDATE SET
            mood = COALESCE(excluded.mood, daily_checkin.mood),
            diet_note = COALESCE(excluded.diet_note, daily_checkin.diet_note),
            exercise_minutes = COALESCE(excluded.exercise_minutes, daily_checkin.exercise_minutes),
            exercise_note = COALESCE(excluded.exercise_note, daily_checkin.exercise_note),
            sleep_hours = COALESCE(excluded.sleep_hours, daily_checkin.sleep_hours),
            weight = COALESCE(excluded.weight, daily_checkin.weight)         
        """,
        (
            target_date,
            entry.mood,
            entry.diet_note,
            entry.exercise_minutes,
            entry.exercise_note,
            entry.sleep_hours,
            entry.weight,
        ),
    )

    
    conn.commit()
    conn.close()

    print(f"Upserted: {target_date}, Weight: {entry.weight}")
    return {"status": "ok", "timestamp": target_date}



@app.get("/checkin")
async def list_checkins():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, timestamp, mood, diet_note, exercise_minutes,
               exercise_note, sleep_hours, weight
        FROM daily_checkin
        ORDER BY id DESC
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows
