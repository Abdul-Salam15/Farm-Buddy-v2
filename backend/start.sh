#!/usr/bin/env bash
# Start Telegram bot in background
python manage.py run_telegram_bot &

# Start web server (single worker — fits Render free tier 512 MB RAM)
gunicorn farmbuddy_web.wsgi:application --bind 0.0.0.0:$PORT --workers 1
