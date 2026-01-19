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


```mermaid
erDiagram
    %% Source & Devices
    SOURCE {
        int id PK
        string name "e.g. iPhone 13, Xiaomi Scale"
        string platform "iOS, Android"
    }

    %% Measurement Types
    MEASUREMENT_TYPE {
        int id PK
        string name "weight, steps, sleep"
        string unit "kg, count, hours"
    }

    %% Core Data
    MEASUREMENT {
        int id PK
        float value
        datetime timestamp
        int source_id FK
        int type_id FK
    }

    %% Daily Aggregation
    DAILY_CHECKIN {
        int id PK
        date date "Unique Index"
        float weight_snapshot
        float sleep_total
        int steps_total
        string mood
        text diet_note
    }

    %% Sync Logs
    SYNC_LOG {
        int id PK
        datetime timestamp
        string status "SUCCESS / FAILED"
        text error_message
    }

    SOURCE ||--o{ MEASUREMENT : generates
    MEASUREMENT_TYPE ||--o{ MEASUREMENT : categorizes
    SOURCE ||--o{ SYNC_LOG : initiates
    DAILY_CHECKIN ||--o{ MEASUREMENT : aggregates
   ```


---

## License

This project is licensed under the **MIT License**.

Copyright (c) 2026 Shuo Mao

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files.
