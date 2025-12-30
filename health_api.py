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
    CREATE TABLE IF NOT EXISTS weigh_in (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        weight REAL NOT NULL,
        note TEXT,
        timestamp TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_checkin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        mood TEXT,
        diet_note TEXT,
        exercise_minutes INTEGER,
        exercise_note TEXT,
        sleep_hours REAL,
        weight REAL
    )
    """)

    conn.commit()
    conn.close()


init_db()


class WeightEntry(BaseModel):
    weight: float
    note: str | None = None


class DailyCheckin(BaseModel):
    mood: str
    diet_note: str
    exercise_minutes: int | None = None
    exercise_note: str | None = None
    sleep_hours: float | None = None
    weight: float | None = None


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
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    ts = datetime.now().isoformat()
    cur.execute(
        """
        INSERT INTO daily_checkin
        (timestamp, mood, diet_note, exercise_minutes,
        exercise_note, sleep_hours, weight)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ts,
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
    return {"status": "ok", "timestamp": ts}


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
