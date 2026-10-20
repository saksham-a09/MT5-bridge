#!/bin/bash
set -e

echo "=========================================================="
echo " Starting MT5 Worker Node Container (Wine + Xvfb)        "
echo "=========================================================="

# 1. Clean stale locks and start virtual X11 display buffer
export DISPLAY=:99
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
Xvfb :99 -screen 0 1024x768x16 -nolisten tcp &
XVFB_PID=$!
echo "[+] Virtual X11 display started on :99 (PID: $XVFB_PID)"

# 2. Configure Wine environment
export WINEDEBUG=-all
export WINEPREFIX=${WINEPREFIX:-/root/.wine}

# Wait briefly for Xvfb initialization
sleep 2

# Cleanup handler on container shutdown
cleanup() {
    echo "[-] Shutting down MT5 worker..."
    kill -TERM "$XVFB_PID" 2>/dev/null || true
    exit 0
}
trap cleanup SIGTERM SIGINT

# 3. Launch Worker Manager under Wine Windows Python
echo "[+] Starting Worker Manager..."
export PYTHONUNBUFFERED=1
PY_BIN="python"
if [ -f "/root/.wine/drive_c/Program Files/Python311/python.exe" ]; then
    PY_BIN="C:\\Program Files\\Python311\\python.exe"
fi
wine "$PY_BIN" -u worker_manager.py "$@"
