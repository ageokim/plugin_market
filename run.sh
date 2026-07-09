#!/usr/bin/env bash
# plugin_market launcher — venv 셋업 후 Streamlit UI 실행
set -e
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
    echo "[setup] python 가상환경 생성..."
    python3 -m venv .venv
fi
source .venv/bin/activate

echo "[setup] 의존성 설치..."
pip install -q -r env/requirements.txt

echo "[run] Streamlit UI 시작 (http://localhost:8501)"
exec streamlit run scripts/app.py
