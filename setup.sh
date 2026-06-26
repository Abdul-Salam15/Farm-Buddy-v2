#!/usr/bin/env bash
set -e

echo "============================================"
echo "   FarmBuddy v2 — Automated Setup"
echo "============================================"
echo ""

# --- Check prerequisites ---
MISSING=""

if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
    MISSING="$MISSING\n  - Python 3.12+  ->  https://www.python.org/downloads/"
fi

if ! command -v node &>/dev/null; then
    MISSING="$MISSING\n  - Node.js 18+   ->  https://nodejs.org/"
fi

if ! command -v pnpm &>/dev/null; then
    if command -v npm &>/dev/null; then
        echo "[*] pnpm not found — installing via npm..."
        npm install -g pnpm
    else
        MISSING="$MISSING\n  - pnpm          ->  run 'npm install -g pnpm' after installing Node.js"
    fi
fi

if ! command -v ffmpeg &>/dev/null; then
    echo "[!] WARNING: ffmpeg not found — voice features will not work."
    echo "    Install it with: sudo apt install ffmpeg  (or brew install ffmpeg on macOS)"
    echo ""
fi

if [ -n "$MISSING" ]; then
    echo "[X] Missing required software:"
    echo -e "$MISSING"
    echo ""
    echo "Install the above, then re-run this script."
    exit 1
fi

PYTHON=$(command -v python3 || command -v python)
echo "[OK] Python:  $($PYTHON --version)"
echo "[OK] Node.js: $(node --version)"
echo "[OK] pnpm:    $(pnpm --version)"
echo ""

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"

# --- Backend setup ---
echo "--------------------------------------------"
echo "  Setting up Backend..."
echo "--------------------------------------------"

cd "$PROJECT_DIR/backend"

if [ ! -d "venv" ]; then
    echo "[*] Creating Python virtual environment..."
    $PYTHON -m venv venv
fi

source venv/bin/activate
echo "[*] Installing Python dependencies..."
pip install -r requirements.txt --quiet

echo "[*] Running database migrations..."
python manage.py migrate --run-syncdb

python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', '', 'admin')
    print('[*] Admin superuser created (username: admin, password: admin)')
else:
    print('[OK] Admin superuser already exists')
"

# --- Create backend .env if missing ---
if [ ! -f ".env" ]; then
    echo "[*] Creating backend/.env template..."
    cat > .env << 'ENVFILE'
SECRET_KEY=change-me-to-a-long-random-string
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
FRONTEND_URL=http://localhost:3000
DATABASE_URL=sqlite:///db.sqlite3

# REQUIRED — get from https://platform.openai.com/api-keys
OPENAI_API_KEY=

# REQUIRED — get from https://openweathermap.org/api
OPENWEATHER_API_KEY=

# OPTIONAL
YARNGPT_API_KEY=
BREVO_API_KEY=
BREVO_SENDER_EMAIL=
TELEGRAM_BOT_TOKEN=
TELEGRAM_BOT_USERNAME=myfarmbuddy_bot
CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=
ENVFILE
    echo ""
    echo "  >>> IMPORTANT: Open backend/.env and add your API keys! <<<"
    echo ""
fi

deactivate

# --- Frontend setup ---
echo "--------------------------------------------"
echo "  Setting up Frontend..."
echo "--------------------------------------------"

cd "$PROJECT_DIR"

if [ ! -f ".env.local" ]; then
    echo "[*] Creating .env.local..."
    echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
fi

echo "[*] Installing frontend dependencies..."
pnpm install --silent

# --- Done ---
echo ""
echo "============================================"
echo "   Setup Complete!"
echo "============================================"
echo ""
echo "  To start the app, run:  ./start.sh"
echo ""
echo "  Or manually:"
echo "    Terminal 1:  cd backend && source venv/bin/activate && python manage.py runserver"
echo "    Terminal 2:  pnpm dev"
echo ""
echo "  Then open:  http://localhost:3000"
echo "============================================"
