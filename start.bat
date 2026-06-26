@echo off
set PROJECT_DIR=%~dp0

echo ============================================
echo    FarmBuddy v2 — Starting App
echo ============================================
echo.

:: Check if setup has been run
if not exist "%PROJECT_DIR%backend\venv" (
    echo [X] Run setup.bat first!
    pause
    exit /b 1
)
if not exist "%PROJECT_DIR%node_modules" (
    echo [X] Run setup.bat first!
    pause
    exit /b 1
)

echo [*] Starting backend on http://localhost:8000 ...
start "FarmBuddy Backend" cmd /k "cd /d %PROJECT_DIR%backend && venv\Scripts\activate && python manage.py runserver"

echo [*] Starting frontend on http://localhost:3000 ...
start "FarmBuddy Frontend" cmd /k "cd /d %PROJECT_DIR% && pnpm dev"

echo.
echo ============================================
echo   App is running!
echo.
echo   Frontend:  http://localhost:3000
echo   Backend:   http://localhost:8000
echo   Admin:     http://localhost:8000/admin
echo.
echo   Close the terminal windows to stop.
echo ============================================
echo.
pause
