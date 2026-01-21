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

-- 1. 核心事件表
-- 建议：在 Sync 过程中可能需要暂时关闭外键检查
CREATE TABLE IF NOT EXISTS observation_event (
    event_id TEXT PRIMARY KEY,        -- UUID
    device_id TEXT NOT NULL,
    observed_at TEXT NOT NULL,        -- ISO8601 String
    observed_ms INTEGER NOT NULL,     -- Epoch ms
    obs_kind TEXT NOT NULL,           -- 'weight' | 'steps' | 'sleep'
    is_valid INTEGER NOT NULL DEFAULT 1,
    superseded_by TEXT DEFAULT NULL,  -- 指向修正它的新 Event ID
    note TEXT DEFAULT NULL,

    CHECK (is_valid IN (0, 1))
    -- [DECISION] 移除 superseded_by 的外键约束，避免同步顺序导致的死锁
    -- FOREIGN KEY (superseded_by) REFERENCES observation_event(event_id)
);

CREATE INDEX IF NOT EXISTS idx_event_device_time 
    ON observation_event(device_id, observed_ms);
CREATE INDEX IF NOT EXISTS idx_event_kind_time 
    ON observation_event(obs_kind, observed_ms);

-- 2. 溯源表
CREATE TABLE IF NOT EXISTS observation_provenance (
    event_id TEXT PRIMARY KEY,
    source_kind TEXT NOT NULL DEFAULT 'unknown', -- healthkit/manual/import
    app_version TEXT DEFAULT NULL,
    ingested_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    provenance_json TEXT DEFAULT NULL,

    FOREIGN KEY (event_id) REFERENCES observation_event(event_id) 
    ON DELETE CASCADE
);

-- 3. Payload: Steps
CREATE TABLE IF NOT EXISTS obs_steps (
    event_id TEXT PRIMARY KEY,
    step_value INTEGER NOT NULL,
    step_mode TEXT NOT NULL, -- 'delta', 'cumulative', 'device_total'
    
    CHECK (step_value >= 0),
    CHECK (step_mode IN ('delta', 'cumulative', 'device_total')),
    FOREIGN KEY (event_id) REFERENCES observation_event(event_id) 
    ON DELETE CASCADE
);

-- 4. Payload: Weight
CREATE TABLE IF NOT EXISTS obs_weight (
    event_id TEXT PRIMARY KEY,
    body_mass_kg REAL NOT NULL,
    -- SQLite Generated Column
    body_mass_01 REAL GENERATED ALWAYS AS (round(body_mass_kg, 1)) VIRTUAL,
    
    CHECK (body_mass_kg > 0),
    FOREIGN KEY (event_id) REFERENCES observation_event(event_id) 
    ON DELETE CASCADE
);

-- 5. Payload: Sleep
CREATE TABLE IF NOT EXISTS obs_sleep (
    event_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    
    CHECK(state <> ''),
    FOREIGN KEY (event_id) REFERENCES observation_event(event_id)
    ON DELETE CASCADE
);

-- 6. Metric Definition
CREATE TABLE IF NOT EXISTS metric_def (
    metric_id TEXT PRIMARY KEY,
    metric_name TEXT NOT NULL UNIQUE,
    watermark TEXT NOT NULL,
    unit TEXT DEFAULT NULL,
    description TEXT DEFAULT NULL
);

-- 7. 修正后的 View
-- 注意：CTE 名字不能重复，逻辑需理顺
CREATE VIEW IF NOT EXISTS fused_minute AS 
WITH base AS (
    SELECT device_id, (observed_ms / 60000) AS minute_bucket,
           observed_ms, event_id, obs_kind
    FROM observation_event 
    WHERE is_valid = 1 AND superseded_by IS NULL 
),
weight_ranked AS (
    SELECT b.device_id, b.minute_bucket, ow.body_mass_01,
           ROW_NUMBER() OVER (PARTITION BY b.device_id, b.minute_bucket ORDER BY b.observed_ms DESC) as rn
    FROM base b 
    JOIN obs_weight ow ON ow.event_id = b.event_id
    WHERE b.obs_kind = 'weight'
),
weight_final AS (
    SELECT device_id, minute_bucket, body_mass_01
    FROM weight_ranked WHERE rn = 1
),
steps_agg AS (
    SELECT b.device_id, b.minute_bucket, 
           SUM(CASE WHEN os.step_mode='delta' THEN os.step_value ELSE 0 END) as steps_delta_sum,
           MAX(CASE WHEN os.step_mode='cumulative' THEN os.step_value ELSE NULL END) AS step_cum_last
    FROM base b
    JOIN obs_steps os ON os.event_id = b.event_id
    WHERE b.obs_kind = 'steps'  -- 修正了原来的 kind 判断
    GROUP BY b.device_id, b.minute_bucket
)
SELECT 
    x.device_id,
    x.minute_bucket,
    datetime(x.minute_bucket * 60, 'unixepoch') AS minute_start_utc, -- 修正时间函数用法
    wp.body_mass_01,
    COALESCE(s.steps_delta_sum, 0) AS steps_delta_sum, 
    s.step_cum_last
FROM (
    SELECT DISTINCT device_id, minute_bucket FROM base 
) x 
LEFT JOIN weight_final wp
    ON wp.device_id = x.device_id AND wp.minute_bucket = x.minute_bucket
LEFT JOIN steps_agg s
    ON s.device_id = x.device_id AND s.minute_bucket = x.minute_bucket;

-- 8. Metric Value
CREATE TABLE IF NOT EXISTS metric_value (
    metric_value_id TEXT PRIMARY KEY,
    metric_id TEXT NOT NULL,
    device_id TEXT NOT NULL,
    window_start_ms INTEGER NOT NULL,
    window_end_ms INTEGER NOT NULL,
    computed_at TEXT NOT NULL,
    value_real REAL DEFAULT NULL,
    value_int INTEGER DEFAULT NULL,
    value_text TEXT DEFAULT NULL,

    CHECK (window_end_ms > window_start_ms),
    FOREIGN KEY (metric_id) REFERENCES metric_def(metric_id)
);

CREATE INDEX IF NOT EXISTS idx_metric_value_device_window
    ON metric_value(device_id, window_start_ms, window_end_ms);

-- 9. Metric Run (Provenance for Metrics)
CREATE TABLE IF NOT EXISTS metric_run (
    metric_value_id TEXT PRIMARY KEY,
    confidence_score REAL NOT NULL,
    missing_data_ratio REAL NOT NULL,
    is_imputed INTEGER NOT NULL DEFAULT 0,
    logic_version TEXT DEFAULT NULL,
    details_json TEXT DEFAULT NULL, 

    CHECK (confidence_score >= 0 AND confidence_score <= 1),
    CHECK (missing_data_ratio >= 0 AND missing_data_ratio <= 1),
    CHECK (is_imputed IN (0, 1)),
    FOREIGN KEY (metric_value_id) REFERENCES metric_value(metric_value_id)
    ON DELETE CASCADE
);

-- 10. Decision Tables
CREATE TABLE IF NOT EXISTS decision_run (
    decision_run_id TEXT PRIMARY KEY, 
    metric_value_id TEXT NOT NULL,
    computed_at TEXT NOT NULL,
    policy_version TEXT DEFAULT NULL,
    -- 修正引用：通常 Decision 基于 Metric Value 产生
    FOREIGN KEY (metric_value_id) REFERENCES metric_value(metric_value_id)
);

CREATE TABLE IF NOT EXISTS decision_result (
    decision_run_id TEXT PRIMARY KEY,
    reversible INTEGER NOT NULL DEFAULT 1,
    explain TEXT DEFAULT NULL,
    action TEXT DEFAULT NULL,
    msg TEXT DEFAULT NULL,
    notify INTEGER NOT NULL DEFAULT 0,

    CHECK (reversible IN (0, 1)),
    CHECK (notify IN (0, 1)),
    FOREIGN KEY (decision_run_id) REFERENCES decision_run(decision_run_id)
);
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
