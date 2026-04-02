#!/bin/sh
set -eu

mkdir -p /var/log/nginx /var/run /app/calorie-tracker/backend/uploads
chown -R www-data:www-data /var/log/nginx /var/run

cd /app/calorie-tracker
uv run --no-sync uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &

exec nginx -g "daemon off;"
