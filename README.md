# Personal Health & Weight tracking Syste

## Overview 
This project is a self-host personal health tracking system build on Raspberry pi 4. 

It allows easy monitoring of weight changes, execrecise habits, sleep patterns and daily wellness notes. 

All data is stored locally and visualized throught an interactive dashboard. 

## Features 

|Component | Technology | Description| 
|----------|------------|------------|
|Backend API| FastAPI + SQLite| Collect and mange health data|
|Data visualization| streamlit| Weight & behavior dashboard| 
|Device| Raspbreey Pi 4|low-cost, self-host server |
|Storage| SQLite| Lightweight database| 


## API Endpoints 

|Method| Endpoint| Function| 
|POST| `/weigh_in` | Record weight entry| 
|GET | `/weigh_in` | Fetch historical weight data| 
|POST| `/checkin` | Daily combined log| 
|GET | `/checkin` | Fetch lastest check-in behavior| 

## Entity Relationship Diagram (ERD)

```
┌────────────────────────┐
│       weigh_in         │
├────────────────────────┤
│ id (PK)                │
│ weight REAL            │
│ note TEXT              │
│ timestamp TEXT         │
└────────────────────────┘

┌────────────────────────┐
│     daily_checkin      │
├────────────────────────┤
│ id (PK)                │
│ timestamp TEXT         │
│ mood TEXT              │
│ diet_note TEXT         │
│ exercise_minutes INT   │
│ exercise_note TEXT     │
│ sleep_hours REAL       │
│ weight REAL            │
└────────────────────────┘

```