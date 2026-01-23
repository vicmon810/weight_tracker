#!/bin/bash
set -e

source venv/bin/activate

# 1. 定义清理函数：当脚本退出或你按 Ctrl+C 时，杀掉所有后台进程
cleanup() {
    echo "Shutting down..."
    kill 0
}

# 2. 捕获退出信号 (这是为了防止 Uvicorn 变成'僵尸进程'一直占用端口)
trap cleanup EXIT

echo "Starting FastAPI Backend on port 8999..."
# 注意：你的 Python 文件名是 health_api.py 吗？如果是 main.py 请改成 main:app
# nohup uvicorn health_api:app --host 0.0.0.0 --port 8999 --reload > logs/back.log 2>&1 &
# nohup uvicorn api.health_api:app --host 0.0.0.0 --port 8999 --reload > logs/back.log 2>&1 &
nohup python -m uvicorn api.health_api:app --host 0.0.0.0 --port 8999 --reload > logs/back.log 2>&1 &
# 等几秒钟让后端先启动
sleep 2

echo "Starting Streamlit Dashboard..."
# 注意：加上 --server.address 0.0.0.0 才能让局域网其他电脑/手机看到
# nohup streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0 
nohup streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0 > logs/front.log 2>&1 &