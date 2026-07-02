#!/usr/bin/env bash
# start.sh — launch both servers in parallel

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   ABHI Banking Assistant — Startup       ║"
echo "╚══════════════════════════════════════════╝"
echo ""
echo "▶  Starting FastAPI backend  (http://localhost:8000)"
echo "▶  Starting React frontend   (http://localhost:5173)"
echo ""
echo "Press Ctrl+C to stop both servers."
echo ""

# Start backend
cd "$SCRIPT_DIR/backend"
uvicorn main:app --reload --port 8000 &
BACKEND_PID=$!

# Start frontend
cd "$SCRIPT_DIR/frontend"
npm run dev -- --port 5173 &
FRONTEND_PID=$!

# Wait and clean up on Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo ''; echo 'Servers stopped.'" EXIT
wait
