#!/usr/bin/env bash
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================"
echo "   FarmBuddy v2 — Starting App"
echo "============================================"
echo ""

# Check if setup has been run
if [ ! -d "$PROJECT_DIR/backend/venv" ] || [ ! -d "$PROJECT_DIR/node_modules" ]; then
    echo "[X] Run ./setup.sh first!"
    exit 1
fi

# Start backend
echo "[*] Starting backend on http://localhost:8000 ..."
cd "$PROJECT_DIR/backend"
source venv/bin/activate
python manage.py runserver &
BACKEND_PID=$!

# Start frontend
echo "[*] Starting frontend on http://localhost:3000 ..."
cd "$PROJECT_DIR"
pnpm dev &
FRONTEND_PID=$!

echo ""
echo "============================================"
echo "  App is running!"
echo ""
echo "  Frontend:  http://localhost:3000"
echo "  Backend:   http://localhost:8000"
echo "  Admin:     http://localhost:8000/admin"
echo ""
echo "  Press Ctrl+C to stop both servers."
echo "============================================"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
