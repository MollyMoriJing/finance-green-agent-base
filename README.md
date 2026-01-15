# Finance Purple Agent (Baseline Example)

A simple A2A-compatible purple agent that serves as a baseline for the Finance Green Agent benchmark.

## Overview

This is a **baseline example** purple agent for the [AgentBeats](https://agentbeats.org) Phase 1 competition. It demonstrates how a purple agent should respond to the evaluation tasks from the Finance Green Agent.

## Features

- ✅ Fully A2A-protocol compatible
- ✅ Responds to all three evaluation tasks:
  - Risk Classification (Task 1)
  - Business Summary (Task 2)
  - Consistency Check (Task 3)
- ✅ Uses LLM (DeepSeek/OpenAI) for intelligent responses
- ✅ Lightweight and easy to run

## Quick Start

### Prerequisites

- Python 3.11+
- Virtual environment (venv or uv)
- OpenRouter API key

### Installation with venv

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -e .

# Configure API key
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY
```

### Installation with uv (Alternative)

```bash
# Install dependencies
uv sync

# Configure API key
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY
```

### Running

```bash
# With venv
.venv/bin/python src/analyst.py --port 9020

# With uv
uv run python src/analyst.py --port 9020
```

## Testing with Green Agent

```bash
# Terminal 1: Start green agent
cd ../finance-green-agent
.venv/bin/python src/server.py --port 9009

# Terminal 2: Start purple agent
cd ../finance-purple-agent
.venv/bin/python src/analyst.py --port 9020

# Terminal 3: Run evaluation
cd ../finance-green-agent
# Use scenario.toml to run evaluation
```

## Response Format

### Task 1: Risk Classification
```json
{
  "task": "risk_classification",
  "risk_classification": ["Market Risk", "Operational Risk", ...]
}
```

### Task 2: Business Summary
```json
{
  "task": "business_summary",
  "business_summary": {
    "industry": "...",
    "products": "...",
    "geography": "..."
  }
}
```

### Task 3: Consistency Check
```json
{
  "task": "consistency_check",
  "consistency_check": ["risk1", "risk2", ...]
}
```

## Project Structure

```
finance-purple-agent/
├── src/
│   └── analyst.py      # Main agent implementation
├── .env.example        # Environment template
├── pyproject.toml      # Dependencies
└── README.md           # This file
```

## License

MIT License

---

## 📋 Phase 1 提交检查清单

> 这是 **Baseline Purple Agent**，需要与 Green Agent 一起提交

### ✅ 已完成
- [x] A2A 协议兼容性
- [x] 三项任务响应逻辑
- [x] LLM 集成（DeepSeek）
- [x] 虚拟环境配置
- [x] README 文档

### 📝 提交时需要

**作为 Green Agent 的配套组件提交**:
1. 在 AgentBeats 平台注册为 "Baseline Purple Agent"
2. GitHub 仓库链接
3. 确保能与 Green Agent 正常通信

**验证步骤**:
```bash
# 1. 启动 Purple Agent
.venv/bin/python src/analyst.py --port 9020

# 2. 检查 Agent Card
curl http://localhost:9020/.well-known/agent-card.json

# 3. 应该看到:
# {
#   "name": "finance-analyst",
#   "skills": [...]
# }
```

### 🎯 在 Demo Video 中展示
- Purple Agent 启动过程
- 与 Green Agent 的交互
- 三项任务的响应示例

---

**注意**: 这是一个简化的 baseline 实现，主要目的是演示 Green Agent 的评估能力。更复杂的 Purple Agent 可以在 Phase 2 开发。
