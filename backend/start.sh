#!/usr/bin/env bash
# run_bot in background
python manage.py run_bot &

# start web server
gunicorn farmbuddy_web.wsgi:application --bind 0.0.0.0:$PORT
