#!/usr/bin/env bash
# CloudWatch 启动脚本 (Linux / macOS)
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "[CloudWatch] 创建虚拟环境..."
    python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "[CloudWatch] 安装/检查依赖..."
pip install -q -r requirements.txt

echo "[CloudWatch] 启动服务 http://0.0.0.0:${CLOUDWATCH_PORT:-8000}"
python main.py
