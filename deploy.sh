#!/bin/bash
set -euo pipefail

PI="${PI_HOST:-admin@100.104.75.80}"

echo "Deploying to $PI..."
rsync -avz \
  --exclude='*.pyc' \
  --exclude='__pycache__' \
  --exclude='watchlist.db' \
  --exclude='config.py' \
  --exclude='monitor.log' \
  --exclude='.git' \
  --exclude='tests/' \
  --exclude='docs/' \
  --exclude='venv/' \
  "$(cd "$(dirname "$0")" && pwd)/" \
  "$PI:~/shoe-price-tracker/"

echo "Restarting service..."
ssh "$PI" "sudo systemctl restart price-tracker"
echo "Done. Flask API is at http://${PI#*@}:5000/status"
