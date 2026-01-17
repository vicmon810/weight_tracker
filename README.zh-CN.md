# HealthPI 嵌入式个人助手

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docs: English](https://img.shields.io/badge/Docs-English-blue.svg)](./README.md)
![Type](https://img.shields.io/badge/Type-Embedded%20Assistant-informational)
![Runtime](https://img.shields.io/badge/Runtime-Ollama-orange)
![Model](https://img.shields.io/badge/Model-Qwen3%200.6b-purple)
![Backend](https://img.shields.io/badge/Backend-FastAPI-teal)
![DB](https://img.shields.io/badge/DB-SQLite-blue)
![GPU](https://img.shields.io/badge/GPU-NVIDIA%20GTX%201060-76B900)

---

## 项目概述

**HealthPI** 是一个以隐私为核心、完全私有化部署的**个人健康统计系统**。它深度集成了一个**嵌入式 AI 助手**。

该助手**不是一个聊天机器人 (Chatbot)**。它是系统的**核心能力**，旨在帮助您理解*您自己的数据*。

---

## 设计原则

### 1. 助手是一种能力，而非一个页面
* 本系统没有独立的“对话页面”。
* 助手的能力嵌入在：
    * 图表旁
    * 指标详情页
    * 洞察卡片 (Insight Cards)
    * 桌面小组件 / Siri

### 2. 系统负责计算，LLM 负责解释
* 所有统计指标与数据均由系统（代码逻辑）确定性计算。
* LLM **永远不直接访问数据库**。
* LLM 仅接收经过处理的**结构化证据**进行自然语言转述。

### 3. 安全边界声明
* **不提供医疗诊断。**
* 不提供处方建议。
* 不可直接控制物理设备。
* *本项目不可替代专业医疗意见，如有不适请立即就医。*

---

## 核心功能

* **指标分析:** 智能解读睡眠、步数、体重、训练负荷等数据。
* **趋势洞察:** 自动生成 7天 / 14天 / 30天 的数据趋势分析。
* **定期报告:** 自动生成周报与月报。
* **本地隐私:** 所有数据与推理均在本地网络完成。

---

## 技术栈

| 层级 | 技术方案 |
| :--- | :--- |
| **iOS 端** | SwiftUI |
| **后端** | FastAPI |
| **数据库** | SQLite |
| **LLM 运行时** | Ollama |
| **模型** | Qwen3 0.6B |
| **部署方式** | 私有化部署 (Self-hosted) |

---

## 模型与运行时

* **模型:** Qwen3 0.6B (Instruct)
* **运行时:** Ollama
* **微调:** LoRA / QLoRA
* **硬件支持:** NVIDIA GTX 1060

---

## 隐私与安全

* **完全自托管:** 无任何云端依赖。
* **零数据库权限:** LLM 无权直接操作数据库，确保数据安全。
* **用户控制:** 用户可随时禁用或移除助手模块。

---

## 许可证 (License)

本项目基于 **MIT 许可证** 开源。

Copyright (c) 2026 Shuo Mao

Permission is hereby granted, free of charge, to any person obtaining a copy.