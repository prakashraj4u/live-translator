#!/bin/bash
cd "$(dirname "$0")"
echo "=== Live Translator: pehli baar setup (internet chahiye) ==="
python3 -m venv venv || { echo "python3 install karo"; exit 1; }
source venv/bin/activate
pip install -r requirements.txt || exit 1
python download_models.py
echo "Setup ho gaya. Ab ./2_RUN.sh chalao."
