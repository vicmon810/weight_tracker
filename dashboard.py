import sqlite3
import pandas as pd
import streamlit as st
from pathlib import Path

DB_PATH = Path(__file__).parent / "health.db"


def load_data():
    if not DB_PATH.exists():
        return pd.DataFrame(columns=["id", "weight", "note", "timestamp"])

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT id, weight, note, timestamp FROM weigh_in ORDER BY id",
        conn,
    )
    conn.close()
    return df


def load_checkins():
    if not DB_PATH.exists():
        return pd.DataFrame(
            columns=[
                "id",
                "timestamp",
                "mood",
                "diet_note",
                "exercise_minutes",
                "exercise_note",
                "sleep_hours",
                "weight",
            ]
        )

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        """
        SELECT id, timestamp, mood, diet_note, exercise_minutes,
               exercise_note, sleep_hours, weight
        FROM daily_checkin
        ORDER BY timestamp
        """,
        conn,
    )
    conn.close()
    return df


st.title("Health & Weight Tracking Dashboard")

# === Daily Check-in Form ===
st.markdown("### Daily Check-in")

with st.form("checkin_form", clear_on_submit=True):
    mood = st.text_input("How do you feel today?")
    diet_note = st.text_area("What did you eat today?")
    exercise_minutes = st.number_input("Exercise minutes", min_value=0, step=10)
    exercise_note = st.text_input("Exercise details")
    sleep_hours = st.number_input("Sleep hours", min_value=0.0, max_value=24.0, step=0.5)
    weight = st.number_input("Weight (kg)", min_value=0.0, step=0.1)

    submitted = st.form_submit_button("Submit")

    if submitted:
        import requests

        url = "http://localhost:8000/checkin"
        data = {
            "mood": mood,
            "diet_note": diet_note,
            "exercise_minutes": int(exercise_minutes),
            "exercise_note": exercise_note,
            "sleep_hours": float(sleep_hours),
            "weight": float(weight),
        }

        resp = requests.post(url, json=data)
        if resp.status_code == 200:
            st.success("Check-in submitted!")
        else:
            st.error("Failed: " + resp.text)


st.header("Weight Tracking")

df_w = load_data()
df_c = load_checkins()

if df_w.empty and df_c.empty:
    st.info("No weight data yet")
else:
    frames = []

    if not df_w.empty:
        t1 = df_w[["timestamp", "weight"]].copy()
        t1["source"] = "weigh_in"
        frames.append(t1)

    if not df_c.empty and df_c["weight"].notna().any():
        t2 = df_c[["timestamp", "weight"]].copy()
        t2 = t2[df_c["weight"].notna()]
        t2["source"] = "checkin"
        frames.append(t2)

    if frames:
        df_all = pd.concat(frames)
        df_all["timestamp"] = pd.to_datetime(df_all["timestamp"])
        df_all = df_all.sort_values("timestamp")
        df_all = df_all.set_index("timestamp")

        st.subheader("Weight Trend")
        st.line_chart(df_all["weight"])

        st.subheader("Recent Weight Entries")
        st.dataframe(df_all[["weight", "source"]].sort_index(ascending=False).head(10))

st.markdown("---")

st.header("Daily Check-ins")

if df_c.empty:
    st.info("No daily check-ins yet")
else:
    st.subheader("Recent Check-ins")
    st.dataframe(df_c.sort_values("timestamp", ascending=False).head(10))

    df_plot = df_c.copy()
    df_plot["timestamp"] = pd.to_datetime(df_plot["timestamp"])
    df_plot = df_plot.set_index("timestamp")

    if df_plot["exercise_minutes"].notna().any():
        st.subheader("Exercise Minutes")
        st.line_chart(df_plot["exercise_minutes"])

    if df_plot["sleep_hours"].notna().any():
        st.subheader("Sleep Hours")
        st.line_chart(df_plot["sleep_hours"])

    last_7 = df_plot.last("7D")

    st.subheader("Last 7 Days Summary")
    col1, col2, col3 = st.columns(3)

    with col1:
        if last_7["weight"].notna().any():
            st.metric("Avg Weight (7D)", f"{last_7['weight'].mean():.1f} kg")
        else:
            st.metric("Avg Weight (7D)", "N/A")

    with col2:
        if last_7["exercise_minutes"].notna().any():
            st.metric("Avg Exercise (7D)", f"{last_7['exercise_minutes'].mean():.0f} min")
        else:
            st.metric("Avg Exercise (7D)", "N/A")

    with col3:
        if last_7["sleep_hours"].notna().any():
            st.metric("Avg Sleep (7D)", f"{last_7['sleep_hours'].mean():.1f} h")
        else:
            st.metric("Avg Sleep (7D)", "N/A")
