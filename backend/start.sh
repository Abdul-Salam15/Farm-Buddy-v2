#!/usr/bin/env bash
# Start full-featured Telegram bot in background (bot_logic.py — all 11 commands)
python manage.py run_bot &

# Start web server (single worker — fits Render free tier 512 MB RAM)
gunicorn farmbuddy_web.wsgi:application --bind 0.0.0.0:$PORT --workers 1
