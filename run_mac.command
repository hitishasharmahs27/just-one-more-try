#!/bin/bash
cd "$(dirname "$0")"
echo "Starting Just One More Try..."
pip install -r src/requirements.txt
python3 src/main.py
