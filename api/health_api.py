import sqlite3
from fastapi import FastAPI,HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import uuid

app = FastAPI()



# print("CWD =", os.getcwd())

DB_PATH = "/home/kris/healthass/store/health.db"

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA foreign_keys = ON;")    
    return conn



SCHEMA_SQL = """
-- Core tables
CREATE TABLE IF NOT EXISTS observation_event (
    event_id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    observed_ms INTEGER NOT NULL,
    obs_kind TEXT NOT NULL,           -- 'weight' | 'steps' | 'sleep_state'
    is_valid INTEGER NOT NULL DEFAULT 1,
    superseded_by TEXT DEFAULT NULL,
    note TEXT DEFAULT NULL,
    CHECK (is_valid IN (0, 1))
);

CREATE INDEX IF NOT EXISTS idx_event_device_time
    ON observation_event(device_id, observed_ms);

CREATE INDEX IF NOT EXISTS idx_event_kind_time
    ON observation_event(obs_kind, observed_ms);

CREATE INDEX IF NOT EXISTS idx_event_superseded
    ON observation_event(device_id, superseded_by);

CREATE TABLE IF NOT EXISTS observation_provenance (
    event_id TEXT PRIMARY KEY,
    source_kind TEXT NOT NULL DEFAULT 'unknown',
    app_version TEXT DEFAULT NULL,
    ingested_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
    provenance_json TEXT DEFAULT NULL,
    FOREIGN KEY (event_id) REFERENCES observation_event(event_id) ON DELETE CASCADE
);

-- Payload tables
CREATE TABLE IF NOT EXISTS obs_steps (
    event_id TEXT PRIMARY KEY,
    step_value INTEGER NOT NULL,
    step_mode TEXT NOT NULL, -- 'delta'|'cumulative'|'device_total'
    CHECK (step_value >= 0),
    CHECK (step_mode IN ('delta', 'cumulative', 'device_total')),
    FOREIGN KEY (event_id) REFERENCES observation_event(event_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS obs_weight (
    event_id TEXT PRIMARY KEY,
    body_mass_kg REAL NOT NULL,
    body_mass_01 REAL GENERATED ALWAYS AS (round(body_mass_kg, 1)) VIRTUAL,
    CHECK (body_mass_kg > 0),
    FOREIGN KEY (event_id) REFERENCES observation_event(event_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS obs_sleep_state (
    event_id TEXT PRIMARY KEY,
    state TEXT NOT NULL,
    CHECK(state <> ''),
    FOREIGN KEY (event_id) REFERENCES observation_event(event_id) ON DELETE CASCADE
);

-- Metrics
CREATE TABLE IF NOT EXISTS metric_def (
    metric_id TEXT PRIMARY KEY,
    metric_name TEXT NOT NULL UNIQUE,
    watermark TEXT NOT NULL,
    unit TEXT DEFAULT NULL,
    description TEXT DEFAULT NULL
);

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
    FOREIGN KEY (metric_value_id) REFERENCES metric_value(metric_value_id) ON DELETE CASCADE
);

-- Decisions
CREATE TABLE IF NOT EXISTS decision_run (
    decision_run_id TEXT PRIMARY KEY,
    metric_value_id TEXT NOT NULL,
    computed_at TEXT NOT NULL,
    policy_version TEXT DEFAULT NULL,
    FOREIGN KEY (metric_value_id) REFERENCES metric_value(metric_value_id) ON DELETE CASCADE
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
    FOREIGN KEY (decision_run_id) REFERENCES decision_run(decision_run_id) ON DELETE CASCADE
);

-- Fused view (minute alignment)
CREATE VIEW IF NOT EXISTS fused_minute AS
WITH base AS (
    SELECT
        device_id,
        CAST(observed_ms / 60000 AS INTEGER) AS minute_bucket,
        observed_ms,
        event_id,
        obs_kind
    FROM observation_event
    WHERE is_valid = 1 AND superseded_by IS NULL
),
weight_ranked AS (
    SELECT
        b.device_id,
        b.minute_bucket,
        ow.body_mass_01,
        ROW_NUMBER() OVER (
            PARTITION BY b.device_id, b.minute_bucket
            ORDER BY b.observed_ms DESC
        ) AS rn
    FROM base b
    JOIN obs_weight ow ON ow.event_id = b.event_id
    WHERE b.obs_kind = 'weight'
),
weight_final AS (
    SELECT device_id, minute_bucket, body_mass_01
    FROM weight_ranked
    WHERE rn = 1
),
steps_agg AS (
    SELECT
        b.device_id,
        b.minute_bucket,
        SUM(CASE WHEN os.step_mode='delta' THEN os.step_value ELSE 0 END) AS steps_delta_sum,
        MAX(CASE WHEN os.step_mode='cumulative' THEN os.step_value ELSE NULL END) AS step_cum_last
    FROM base b
    JOIN obs_steps os ON os.event_id = b.event_id
    WHERE b.obs_kind = 'steps'
    GROUP BY b.device_id, b.minute_bucket
)
SELECT
    x.device_id,
    x.minute_bucket,
    datetime(x.minute_bucket * 60, 'unixepoch') AS minute_start_utc,
    wf.body_mass_01,
    COALESCE(sa.steps_delta_sum, 0) AS steps_delta_sum,
    sa.step_cum_last
FROM (SELECT DISTINCT device_id, minute_bucket FROM base) x
LEFT JOIN weight_final wf
    ON wf.device_id = x.device_id AND wf.minute_bucket = x.minute_bucket
LEFT JOIN steps_agg sa
    ON sa.device_id = x.device_id AND sa.minute_bucket = x.minute_bucket;
"""

def init_db():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    try:
        # # connection-level pragmas
        # conn.execute("PRAGMA foreign_keys = ON;")
        # conn.execute("PRAGMA journal_mode = WAL;")
        # conn.execute("PRAGMA synchronous = NORMAL;")
        # conn.execute("PRAGMA busy_timeout = 5000;")

        # run schema
        # cur = conn.cursor()
        # cur.execute(SCHEMA_SQL)
        conn.executescript(SCHEMA_SQL)
        # optional: verify
        jm = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        fk = conn.execute("PRAGMA foreign_keys;").fetchone()[0]
        print(f"SQLite ready: journal_mode={jm}, foreign_keys={fk}")
    finally:
        conn.commit()
        conn.close()



class ObservationEventIn(BaseModel):
    event_id: str
    device_id: str
    observed_at: str 
    observed_ms: int 
    obs_kind: str 
    is_valid: bool = True
    superseded_by: Optional[str] =  None
    note: Optional[str] =  None

class ObservationProvenanceIn(BaseModel):
    event_id: str
    source_kind: str = "unknown"
    app_version: Optional[str] =  None
    ingested_at: Optional[str] =  None
    provenance_json: Optional[str] =  None

class ObsStepsIn(BaseModel):
    event_id: str 
    step_value: int 
    step_mode: str 

class ObsWeightIn(BaseModel):
    event_id: str
    body_mass_kg: float 

class ObsSleepIn(BaseModel):
    event_id: str 
    state: str| None 

class MetricDefIn(BaseModel):
    metric_id: str 
    metric_name: str 
    watermark: str 
    unit: Optional[str] = None
    description : Optional[str] = None

class MetricValueIn(BaseModel):
    metric_value_id: str
    metric_id:str
    device_id:str
    window_start_ms: int
    window_end_ms: int
    computed_at: str
    value_real: Optional[float] = None
    value_int: Optional[int] = None
    value_text: Optional[str] = None



class MetricRunIn (BaseModel):
    metric_value_id: str
    confidence_score:float
    missing_data_ratio: float
    is_imputed: Optional[int] = 1
    logic_version: Optional[str] = None
    details_json: Optional[str] = None
    

class DecisionRunIn(BaseModel):
    decision_run_id: str
    metric_value_id: str
    computed_at: str 
    policy_version: Optional[str] = None


class DecisionResultIn(BaseModel):
    decision_run_id: str 
    reversible: int 
    explain: Optional[str] = None
    action: Optional[str] = None
    msg: Optional[str] = None
    notify: bool


@app.on_event("startup")
def on_startup():
    init_db()

@app.post("/observation_event")
async def add_observation(entry:ObservationEventIn):
    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO observation_event
                (event_id,device_id ,observed_at,observed_ms,obs_kind 
                ,is_valid,superseded_by ,note) values
                (?,?,?,?,?,?,?,?)
                """,
                (entry.event_id,
                entry.device_id, 
                entry.observed_at,
                entry.observed_ms, 
                entry.obs_kind, 
                int(entry.is_valid),
                entry.superseded_by, 
                entry.note)
            )
            
        return{"status": "ok", "Event Id": entry.event_id}
    except sqlite3.IntegrityError as e:
            raise HTTPException(status_code=400, detail=str(e))
    except sqlite3.OperationalError as e:
            raise HTTPException(status_code=500, detail=f"DB error: {e}")
    finally:
            conn.close()
    

@app.post("/observation_provenance")
async def add_provenance(entry:ObservationProvenanceIn):
    try:
        with get_conn() as conn:
            conn.execute(
                """INSERT INTO observation_provenance
                (event_id,source_kind,app_version,ingested_at,provenance_json) values(?,?,?,?,?)"""
                ,
                (
                entry.event_id, 
                entry.source_kind,
                entry.app_version,
                entry.ingested_at, 
                entry.provenance_json
                )
            )
       
        return {"status": "OKAY", "Provenance Status": entry.source_kind}
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Catch other potential general errors
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    finally:
        conn.close()



@app.post("/obs_steps")
async def add_steps(entry:ObsStepsIn):
    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO obs_steps
                (event_id,step_value,step_mode) values(?,?,?)
                """,
                (entry.event_id, 
                entry.step_value,
                entry.step_mode)
            )
     
        return {"status": "Okay", "Event Id": entry.event_id}
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Catch other potential general errors
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {e}")
    finally:
        conn.close()


@app.post("/obs_weight")
async def add_weight(entry:ObsWeightIn):
    try:
        with get_conn() as conn:
            conn.execute(
                "INSERT INTO obs_weight(event_id,body_mass_kg) values(?,?)",
                (entry.event_id, entry.body_mass_kg)
            )
            
        return {"status:": "200", "Event Id": entry.event_id}
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'An unexpected error occured:{e}')
    finally:
        conn.close()

@app.post("/obs_sleep_state")
async def add_sleep(entry: ObsSleepIn):        
    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO obs_sleep_state
                (event_id,state)values
                (?,?)
                """,
                (entry.event_id, entry.state)
            )
            
        return {"status:": "200", "Event Id": entry.event_id}
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occured: {e}")
    finally:
        conn.close()

@app.post("/metric_def")        
async def add_metric_def (entry:MetricDefIn):
    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO metric_def
                (metric_id,metric_name,watermark,unit,description)
                values(?,?,?,?,?)
                """,
                (entry.metric_id, 
                entry.metric_name,
                entry.watermark, 
                entry.unit,
                entry.description)
            )
            
        
        return {"status:": "200", "Event Id": entry.metric_id}
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occured: {e}")
    finally:
        conn.close()

    
@app.post("/metric_value")
async def add_metric_value(entry: MetricValueIn):
    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO metric_value(
                metric_value_id,metric_id,device_id,window_start_ms,
                window_end_ms, computed_at, value_real, value_int, value_text)
                values(?,?,?,?,?,?,?,?,?)
                """,
                (
                    entry.metric_value_id,
                    entry.metric_id,
                    entry.device_id,
                    entry.window_start_ms,
                    entry.window_end_ms,
                    entry.computed_at,
                    entry.value_real,
                    entry.value_int,
                    entry.value_text
                )
            )
            
        
        return {"status:": "200", "Event Id": entry.metric_value_id}
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occured: {e}")
    finally:
        conn.close()


@app.post("/metric_run")
async def add_metric_run(entry: MetricRunIn):
    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO metric_run
                (metric_value_id ,confidence_score ,missing_data_ratio ,
                is_imputed,logic_version,details_json)
                values(?,?,?,?,?,?)
                """,
                (
                    entry.metric_value_id,
                    entry.confidence_score,
                    entry.missing_data_ratio,
                    entry.is_imputed,
                    entry.logic_version,
                    entry.details_json
                )
            )
        
        return {"status:": "200", "Event Id": entry.metric_value_id}
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occured: {e}")
    finally:
        conn.close()


@app.post("/decision_run")
async def add_decision_run(entry:DecisionRunIn):
    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO decision_run
                (decision_run_id ,metric_value_id ,computed_at ,policy_version)
                values(?,?,?,?)
                """, (
                    entry.decision_run_id,
                    entry.metric_value_id,
                    entry.computed_at,
                    entry.policy_version
                )
            )
        
        return {"status:": "200", "Event Id": entry.decision_run_id}
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occured: {e}")
    finally:
        conn.close()

@app.post("/decision_result")
async def add_decision_result(entry:DecisionResultIn):
    try:
        with get_conn() as conn:
            conn.execute(
                """
                INSERT INTO decision_result
                (decision_run_id, reversible,explain,action,msg,notify)
                values (?,?,?,?,?,?)
                """,
                (
                    entry.decision_run_id,
                    entry.reversible,
                    entry.explain,
                    entry.action,
                    entry.msg,
                    entry.notify
                )
            )
        
        return {"status:": "200", "Event Id": entry.decision_run_id}
    except sqlite3.IntegrityError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occured: {e}")
    finally:
        conn.close()