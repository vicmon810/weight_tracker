# HealthPI Embedded Personal Assistant 

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![DOC 中文](https://img.shields.io/badge/Docs-中文-red.svg)](#中文)
[![DOC ENGLISH](https://img.shields.io/badge/Docs-English-blue.svg)](#English)
![type](https://img.shields.io/badge/Type-Embedded%20Assistant-infomational)
![Runtime](https://img.shields.io/badge/Runtime-Ollama-orange)
![Model](https://img.shields.io/badge/Model-Qwen3%200.6b-purple)
![Backend](https://img.shields.io/badge/Backend-FastAPI-teal)
![DB](https://img.shields.io/badge/DB-SQLite-blue)
![GPU](https://img.shields.io/badge/GPU-NVIDIA%20GTX%201060-76B900)

---

## Overview 

HealthPi is a **privacy-first ,self-hosted personal health system**  with a **deeply embedded AI assistant**

This assistant is **NOT A CHATBOX** 

It is a **SYSTEM CAPABILITY** that helps you understand *your own data*
---


<details open>
        <summary><strong>English</strong></summary>

---

## English

## What is HealthPI?

**HealthPI** is a private-first, fully self-hosted **personal health and statics system** with a **deeply embedded AI assistant**

The assistant is **NOT A CHATBOT** 

It is a **System-level capability** that explains *your own data* 

--- 

## Core principle 

### 1 Assistant is a capability, not a page 

- No "Assistant page"
- Assistant lives inside:
  - charts
  - Metrics
  - Insight cards
  - Widgets/Siri

### 2 System computes, LLM explains 

- All metrics are computed deterministically
- LLM never touches raw database
- LLM consumes structured evidence only

### 3 Explictit Safety boundaries 

- No Medical diagnosis
- No prescriptions
- No autonomous device control
---
## Key Feature 

- Metric explanations(sleep, steps, weight, training)
- Trend analysis
- Automated insights
- Weekly/Monthly reports
- Fully local, privacy-first

---

</details>

<details><summary>
                <strong>
                        中文说明
                </strong>
        </summary>

---

## 中文    

## 什么是 HealthPI
**HealthPI** 是一个以隐私为核心的，完全自处理的**个人健康与统计系统**并且深度嵌入与AI助手用于：

        - 解释您的健康与个人统计数据
        - 自动生成趋势报告，洞察，周报

### HealthPI 的核心理念

- HealthPi 不是一个聊天机器人
- 是系统的一部分
- 了解并且知道您当前的数据
- 自动解释，总结，提醒

--- 

## 设计原则
---
### 1. Assistant 是系统能力并非页面

- 不需要助手页面
- 助手存在于：
  - 图表旁
  - 指标页面
  - Widget/ Siri

### 2. 系统负责计算，LLM只用于解释数据

- 全部系统统计与指标由系统计算
- LLM **永远不直接访问数据库**
- LLM 只负责**结构化证据**

### 3. 安全声明

- 本项目不代表任何专业的医生意见
- 本项目不可作用于现实设备
- 本项目不具备任何专业医生处方意见
- 本项目不可替代医疗诊断
- 如有不适请立即就医
---
## 核心能力

- 指标分析（睡眠，步数，体重，训练量等）
- 趋势分析（7天/14天/30天)
- 周报/月报生成
- 本地隐私优先
---  

</details>


---

## Model & Runtime 

- **Model**: Qwen3 0.6B (INstruct)
- **Runtime**: Ollama
- **Fine-tuning**: LoRA/ QLoRA
- **GPU**: NVIDIA GTX 1060

---

## Technology Stack

| layer | Stack| 
|------|-------|
|IOS | SwiftUI| 
|Backend| FastAPI|
|Database| SQLite| 
|LLM Runtime| Ollama|
|Model| Qwen3 0.6B|
|Deployment| Self-hosted| 

---

## Privacy & Security 

- Fully self-hosted
- No cloud dependency
- LLM has NO **DB** access
- User can disable or remove assistant

---

## License 

This project is licensed under the **MIT license**.

MIT License 

Copyright(c) 2026 Shuo Mao 

Permission is hereby granted, free to change, to any person obtaining a copy.
