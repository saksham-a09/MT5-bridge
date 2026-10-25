#!/bin/bash
set -e

echo "=========================================================="
echo " Starting MT5 Worker Node Container (Wine + Xvfb)        "
echo "=========================================================="

# 1. Clean stale locks and start low-footprint virtual X11 display buffer (320x240x8 in /dev/shm)
export DISPLAY=:99
rm -f /tmp/.X99-lock /tmp/.X11-unix/X99
FB_OPT=""
if [ -d "/dev/shm" ]; then
    FB_OPT="-fbdir /dev/shm"
fi
Xvfb :99 -screen 0 320x240x8 -nocursor -nolisten tcp -extension Composite -extension GLX -extension RANDR $FB_OPT &
XVFB_PID=$!
echo "[+] Ultra-low-footprint virtual X11 display started on :99 (PID: $XVFB_PID, 320x240x8)"

# 2. Configure Wine environment (disable 3D acceleration, audio, and debug logging)
export WINEDEBUG=-all
export WINEARCH=win64
export WINEPREFIX=${WINEPREFIX:-/root/.wine}
export WINEDLLOVERRIDES="mscoree,mshtml,winepulse,winealsa,d3d9,d3d11,dxgi,opengl32="
export PATH="/opt/wine-stable/bin:${PATH}"
export PYTHONDONTWRITEBYTECODE=1
export PYTHONOPTIMIZE=1

# Keep wineserver persistent in RAM to eliminate repeated process spin-up overhead
wineserver -p 2>/dev/null || true

# Wait briefly for Xvfb initialization
sleep 2

# Cleanup handler on container shutdown
cleanup() {
    echo "[-] Shutting down MT5 worker..."
    kill -TERM "$XVFB_PID" 2>/dev/null || true
    wineserver -k 2>/dev/null || true
    exit 0
}
trap cleanup SIGTERM SIGINT

# 3. Launch Worker Manager under Wine Windows Python
echo "[+] Starting Worker Manager..."
export PYTHONUNBUFFERED=1
wine python -u worker_manager.py "$@"
