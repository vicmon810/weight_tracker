# HealthPI Embedded Personal Assistant

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docs: 中文](https://img.shields.io/badge/Docs-中文-red.svg)](./README.zh-CN.md)
![Type](https://img.shields.io/badge/Type-Embedded%20Assistant-informational)
![Runtime](https://img.shields.io/badge/Runtime-Ollama-orange)
![Model](https://img.shields.io/badge/Model-Qwen3%200.6b-purple)
![Backend](https://img.shields.io/badge/Backend-FastAPI-teal)
![DB](https://img.shields.io/badge/DB-SQLite-blue)
![GPU](https://img.shields.io/badge/GPU-NVIDIA%20GTX%201060-76B900)

---

## Overview

**HealthPI** is a privacy-first, self-hosted **personal health tracking system** with a **deeply embedded AI assistant**.

This assistant is **NOT A CHATBOT**. It is a **SYSTEM CAPABILITY** that helps you understand *your own data*.

---

## Core Principles

### 1. Assistant is a Capability, Not a Page
* No dedicated "Assistant Page".
* The assistant lives inside:
    * Charts
    * Metrics
    * Insight Cards
    * Widgets / Siri

### 2. System Computes, LLM Explains
* All metrics are computed deterministically by the system (Python/Pandas).
* The LLM **never** touches the raw database directly.
* The LLM consumes only **structured evidence** provided by the backend.

### 3. Explicit Safety Boundaries
* **No Medical Diagnosis.**
* No prescriptions.
* No autonomous device control.

---

## Key Features

* **Metric Explanations:** Contextual insights for sleep, steps, weight, and training load.
* **Trend Analysis:** Automated analysis of 7-day, 14-day, and 30-day trends.
* **Automated Reporting:** Weekly and Monthly summaries generated automatically.
* **Privacy First:** Fully local execution; no data leaves your network.

---

## Technology Stack

| Layer | Stack |
| :--- | :--- |
| **iOS App** | SwiftUI |
| **Backend** | FastAPI (Python) |
| **Database** | SQLite |
| **LLM Runtime** | Ollama |
| **Model** | Qwen3 0.6B (Instruct) |
| **Hardware** | Raspberry Pi 4 + NVIDIA GTX 1060 (Host) |

---

## Model & Runtime

* **Model:** Qwen3 0.6B (Instruct)
* **Runtime:** Ollama
* **Fine-tuning:** LoRA / QLoRA
* **Inference:** Local GPU (NVIDIA GTX 1060)

---

## Privacy & Security

* **Fully Self-Hosted:** No cloud dependency.
* **Zero DB Access:** The LLM cannot query the database; it only reads pre-processed JSON contexts.
* **User Control:** You can disable or remove the assistant module at any time.

---



## Entity Relationship Diagram (ERD)

```
erDiagram

    %% =========================
    %% Data Sources / Devices
    %% =========================
    SOURCE {
        int id PK
        string name "iPhone 13, Xiaomi Scale"
        string platform "iOS, Android, BLE"
        string manufacturer
        string model
        datetime created_at
    }

    %% =========================
    %% Measurement Types
    %% =========================
    MEASUREMENT_TYPE {
        int id PK
        string name "weight, steps, sleep, hr"
        string unit "kg, count, hours, bpm"
        string category "body, activity, sleep"
    }

    %% =========================
    %% Raw Measurements (Atomic)
    %% =========================
    MEASUREMENT {
        int id PK
        float value
        datetime timestamp
        int source_id FK
        int type_id FK
        string granularity "instant, interval"
        datetime created_at
    }

    %% =========================
    %% Daily Aggregates (System Computed)
    %% =========================
    DAILY_CHECKIN {
        int id PK
        date date "UNIQUE"
        float weight_snapshot
        float sleep_total_hours
        int steps_total
        float training_load
        string mood
        text diet_note
        datetime created_at
    }

    %% =========================
    %% Mapping: Raw → Daily
    %% =========================
    DAILY_MEASUREMENT_MAP {
        int id PK
        int daily_checkin_id FK
        int measurement_id FK
    }

    %% =========================
    %% Computed Metrics (Evidence)
    %% =========================
    METRIC {
        int id PK
        string name "7d_avg_steps, sleep_debt"
        string value_type "float, int, json"
        string unit
        string window "7d, 14d, 30d"
    }

    METRIC_VALUE {
        int id PK
        int metric_id FK
        date date
        text value_json
        datetime computed_at
    }

    %% =========================
    %% LLM Insight Outputs
    %% =========================
    INSIGHT {
        int id PK
        date date
        string scope "daily, weekly, monthly"
        text explanation
        text evidence_json
        string model_version
        datetime generated_at
    }

    %% =========================
    %% Sync & Audit
    %% =========================
    SYNC_LOG {
        int id PK
        int source_id FK
        datetime timestamp
        string status "SUCCESS, FAILED"
        text error_message
    }

    %% =========================
    %% Relationships
    %% =========================
    SOURCE ||--o{ MEASUREMENT : produces
    MEASUREMENT_TYPE ||--o{ MEASUREMENT : classifies

    SOURCE ||--o{ SYNC_LOG : initiates

    DAILY_CHECKIN ||--o{ DAILY_MEASUREMENT_MAP : aggregates
    MEASUREMENT ||--o{ DAILY_MEASUREMENT_MAP : contributes

    METRIC ||--o{ METRIC_VALUE : defines
    DAILY_CHECKIN ||--o{ METRIC_VALUE : summarized_by

    DAILY_CHECKIN ||--o{ INSIGHT : explained_by


```


---

## License

This project is licensed under the **MIT License**.

Copyright (c) 2026 Shuo Mao

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files.
