@echo off
echo ============================================
echo    FarmBuddy v2 — Automated Setup
echo ============================================
echo.

:: --- Check prerequisites ---
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [X] Python not found. Install Python 3.12+ from https://www.python.org/downloads/
    echo     Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

where node >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [X] Node.js not found. Install Node.js 18+ from https://nodejs.org/
    pause
    exit /b 1
)

where pnpm >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [*] pnpm not found — installing via npm...
    call npm install -g pnpm
    if %ERRORLEVEL% neq 0 (
        echo [X] Failed to install pnpm. Run: npm install -g pnpm
        pause
        exit /b 1
    )
)

where ffmpeg >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [!] WARNING: ffmpeg not found — voice features will not work.
    echo     Download from https://ffmpeg.org/download.html and add to PATH.
    echo.
)

for /f "tokens=*" %%v in ('python --version') do echo [OK] %%v
for /f "tokens=*" %%v in ('node --version') do echo [OK] Node.js %%v
for /f "tokens=*" %%v in ('pnpm --version') do echo [OK] pnpm %%v
echo.

set PROJECT_DIR=%~dp0

:: --- Backend setup ---
echo --------------------------------------------
echo   Setting up Backend...
echo --------------------------------------------

cd /d "%PROJECT_DIR%backend"

if not exist "venv" (
    echo [*] Creating Python virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat

echo [*] Installing Python dependencies...
pip install -r requirements.txt --quiet

echo [*] Running database migrations...
python manage.py migrate --run-syncdb

python manage.py shell -c "from django.contrib.auth import get_user_model; User = get_user_model(); print('[*] Admin superuser created (username: admin, password: admin)') if not User.objects.filter(username='admin').exists() and User.objects.create_superuser('admin', '', 'admin') or not User.objects.filter(username='admin').exists() else print('[OK] Admin superuser already exists')"

:: --- Create backend .env if missing ---
if not exist ".env" (
    echo [*] Creating backend\.env template...
    (
        echo SECRET_KEY=change-me-to-a-long-random-string
        echo DEBUG=True
        echo ALLOWED_HOSTS=localhost,127.0.0.1
        echo FRONTEND_URL=http://localhost:3000
        echo DATABASE_URL=sqlite:///db.sqlite3
        echo.
        echo # REQUIRED — get from https://platform.openai.com/api-keys
        echo OPENAI_API_KEY=
        echo.
        echo # REQUIRED — get from https://openweathermap.org/api
        echo OPENWEATHER_API_KEY=
        echo.
        echo # OPTIONAL
        echo YARNGPT_API_KEY=
        echo BREVO_API_KEY=
        echo BREVO_SENDER_EMAIL=
        echo TELEGRAM_BOT_TOKEN=
        echo TELEGRAM_BOT_USERNAME=myfarmbuddy_bot
        echo CLOUDINARY_CLOUD_NAME=
        echo CLOUDINARY_API_KEY=
        echo CLOUDINARY_API_SECRET=
    ) > .env
    echo.
    echo   ^^>^^>^^> IMPORTANT: Open backend\.env and add your API keys! ^^<^^<^^<
    echo.
)

call deactivate

:: --- Frontend setup ---
echo --------------------------------------------
echo   Setting up Frontend...
echo --------------------------------------------

cd /d "%PROJECT_DIR%"

if not exist ".env.local" (
    echo [*] Creating .env.local...
    echo NEXT_PUBLIC_API_URL=http://localhost:8000> .env.local
)

echo [*] Installing frontend dependencies...
call pnpm install --silent

:: --- Done ---
echo.
echo ============================================
echo    Setup Complete!
echo ============================================
echo.
echo   To start the app, run:  start.bat
echo.
echo   Or manually:
echo     Terminal 1:  cd backend ^& venv\Scripts\activate ^& python manage.py runserver
echo     Terminal 2:  pnpm dev
echo.
echo   Then open:  http://localhost:3000
echo ============================================
echo.
pause
