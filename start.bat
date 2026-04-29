@echo off
echo ==========================================
echo 🛡️ Starting CommentGuard v3.0...
echo ==========================================

setlocal enabledelayedexpansion

:: Check Port 8000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :8000 ^| findstr LISTENING') do set PID_8000=%%a
if defined PID_8000 (
    echo ⚠️ Port 8000 is already in use.
    set /p kill_8000="Do you want to kill it to proceed? (y/n): "
    if /i "!kill_8000!"=="y" (
        taskkill /F /PID !PID_8000! >nul
        echo ✅ Killed process on port 8000.
    ) else (
        echo Exiting...
        exit /b 1
    )
)

:: Check Port 3000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :3000 ^| findstr LISTENING') do set PID_3000=%%a
if defined PID_3000 (
    echo ⚠️ Port 3000 is already in use.
    set /p kill_3000="Do you want to kill it to proceed? (y/n): "
    if /i "!kill_3000!"=="y" (
        taskkill /F /PID !PID_3000! >nul
        echo ✅ Killed process on port 3000.
    ) else (
        echo Exiting...
        exit /b 1
    )
)

echo [1/2] Booting up AI Backend (FastAPI)...
cd backend
if not exist "venv\" (
    echo Creating virtual environment...
    python -m venv venv
)
call venv\Scripts\activate.bat
pip install -r requirements.txt -q
start "CommentGuard API" cmd /c "uvicorn app.main:app --host 0.0.0.0 --port 8000"
cd ..

echo [2/2] Booting up Live Dashboard (React)...
cd dashboard
call npm install --silent
start "CommentGuard Dashboard" cmd /c "npm run dev"
cd ..

echo.
echo ✅ CommentGuard is completely LIVE!
echo ------------------------------------------------
echo 🧠 API Backend:   http://localhost:8000/docs
echo 📈 Dashboard:     http://localhost:3000
echo ------------------------------------------------
echo You can close this window at any time. To stop the servers, close the two pop-up terminal windows.
pause
