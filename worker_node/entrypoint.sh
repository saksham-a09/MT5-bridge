#!/bin/bash
set -e

echo "=========================================================="
echo " Starting MT5 Worker Node Container (Wine + Xvfb)        "
echo "=========================================================="

# 1. Start virtual X11 display buffer for headless MT5 execution
export DISPLAY=:99
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
wine python worker_manager.py "$@"
