#!/bin/bash

# CommentGuard 1-Click Startup Script (Mac/Linux)

echo -e "\033[1;36m🛡️ Starting CommentGuard v3.0...\033[0m"

# Helper to check and kill ports
check_port() {
    PORT=$1
    PID=$(lsof -ti:$PORT 2>/dev/null)
    if [ ! -z "$PID" ]; then
        echo -e "\033[1;33m⚠️ Port $PORT is already in use.\033[0m"
        read -p "Do you want to kill the existing process to proceed? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            kill -9 $PID
            echo -e "\033[1;32m✅ Killed process on port $PORT.\033[0m"
        else
            echo "Exiting startup. Please free up port $PORT."
            exit 1
        fi
    fi
}

check_port 8000
check_port 3000

# 1. Start the FastAPI Backend
echo -e "\033[1;32m[1/2] Booting up AI Backend (FastAPI)...\033[0m"
cd backend
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt -q
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# 2. Start the React Dashboard
echo -e "\033[1;32m[2/2] Booting up Live Dashboard (React)...\033[0m"
cd dashboard
npm install --silent
npm run dev &
DASHBOARD_PID=$!
cd ..

echo -e "\n\033[1;32m✅ CommentGuard is completely LIVE!\033[0m"
echo -e "------------------------------------------------"
echo -e "🧠 API Backend:   \033[4;34mhttp://localhost:8000/docs\033[0m"
echo -e "📈 Dashboard:     \033[4;34mhttp://localhost:3000\033[0m"
echo -e "------------------------------------------------"
echo -e "Press Ctrl+C to shut everything down."

# Wait for user to press Ctrl+C
trap "echo -e '\n\033[1;31mShutting down CommentGuard...\033[0m'; kill $BACKEND_PID $DASHBOARD_PID; exit" INT
wait
