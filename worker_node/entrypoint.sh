#!/bin/bash
set -e

echo "=========================================================="
echo " Starting MT5 Worker Node Container (Wine + Xvfb)        "
echo "=========================================================="

# 1. Dynamically select an unused virtual X11 display (prevents clashes when running multiple containers)
is_display_in_use() {
    local d="$1"
    local num="${d#:}"
    if [ -e "/tmp/.X${num}-lock" ] || [ -e "/tmp/.X11-unix/X${num}" ]; then
        return 0
    fi
    if [ -f /proc/net/unix ] && grep -q "/tmp/\.X11-unix/X${num}\b" /proc/net/unix; then
        return 0
    fi
    return 1
}

# If DISPLAY is explicitly specified and free, keep it. Otherwise, auto-assign next free display starting at 99
if [ -z "$DISPLAY" ] || is_display_in_use "$DISPLAY"; then
    for i in $(seq 99 999); do
        if ! is_display_in_use ":$i"; then
            export DISPLAY=":$i"
            break
        fi
    done
fi

DISP_NUM="${DISPLAY#:}"
rm -f "/tmp/.X${DISP_NUM}-lock" "/tmp/.X11-unix/X${DISP_NUM}"
Xvfb "$DISPLAY" -screen 0 800x600x16 -nolisten tcp -maxclients 2048 &
XVFB_PID=$!
echo "[+] Virtual X11 display started on $DISPLAY (PID: $XVFB_PID, maxclients=2048)"

# 2. Configure Wine environment (disable audio and debug logging to eliminate CPU overhead)
export WINEDEBUG=-all
export WINEARCH=win64
export WINEPREFIX=${WINEPREFIX:-/root/.wine}
export WINEDLLOVERRIDES="mscoree,mshtml,winepulse,winealsa="
export PATH="/opt/wine-stable/bin:${PATH}"

# Wait briefly for Xvfb initialization
sleep 2

# 2.5 Block MetaQuotes LiveUpdate domains to permanently disable MT5 auto-updates
if ! grep -q "liveupdate.metaquotes.net" /etc/hosts 2>/dev/null; then
    echo "127.0.0.1 liveupdate.metaquotes.net downloads.metaquotes.net updates.metaquotes.net" >> /etc/hosts 2>/dev/null || true
fi
pkill -9 -f liveupdate 2>/dev/null || true

for user_dir in "${WINEPREFIX}/drive_c/users"/*; do
    if [ -d "$user_dir" ]; then
        MQ_DIR="$user_dir/AppData/Roaming/MetaQuotes"
        mkdir -p "$MQ_DIR" 2>/dev/null || true
        rm -rf "$MQ_DIR/WebInstall" 2>/dev/null || true
        touch "$MQ_DIR/WebInstall" 2>/dev/null || true
        chmod 444 "$MQ_DIR/WebInstall" 2>/dev/null || true

        # Block LiveUpdate by making 'liveupdate' an empty read-only file in all Terminal hash directories
        if [ -d "$MQ_DIR/Terminal" ]; then
            for term_hash in "$MQ_DIR/Terminal"/*; do
                if [ -d "$term_hash" ]; then
                    rm -rf "$term_hash/liveupdate" 2>/dev/null || true
                    touch "$term_hash/liveupdate" 2>/dev/null || true
                    chmod 444 "$term_hash/liveupdate" 2>/dev/null || true
                fi
            done
        fi
    fi
done

# Start lightweight background watchdog to immediately terminate any rogue LiveUpdate process
(
    while true; do
        sleep 5
        pkill -9 -f liveupdate 2>/dev/null || true
    done
) &
WATCHDOG_PID=$!

# 2.6 Link shared /app_data volume paths (unique per NODE_ID to avoid conflicts across multiple containers)
NODE_SUFFIX="${NODE_ID:-${HOSTNAME:-default}}"
CLIENTS_DIR="${CLIENTS_DIR:-/app_data/worker_node/CLIENTS_${NODE_SUFFIX}}"

# Ensure MASTER_MT5_DIR resolves to a valid existing directory inside the container
RESOLVED_MASTER=""
if [ -n "$MASTER_MT5_DIR" ] && [ -d "$MASTER_MT5_DIR" ] && { [ -f "$MASTER_MT5_DIR/terminal64.exe" ] || [ -f "$MASTER_MT5_DIR/terminal.exe" ]; }; then
    RESOLVED_MASTER="$MASTER_MT5_DIR"
fi

if [ -z "$RESOLVED_MASTER" ]; then
    for cand in \
        "/app_data/Master MT5" \
        "/app_data/master_mt5" \
        "/app/Master MT5" \
        "/app/master_mt5"; do
        if [ -d "$cand" ] && { [ -f "$cand/terminal64.exe" ] || [ -f "$cand/terminal.exe" ]; }; then
            RESOLVED_MASTER="$cand"
            break
        fi
    done
fi

if [ -z "$RESOLVED_MASTER" ]; then
    RESOLVED_MASTER="${MASTER_MT5_DIR:-/app_data/Master MT5}"
fi
export MASTER_MT5_DIR="$RESOLVED_MASTER"

if [ -d "/app_data" ]; then
    mkdir -p "$CLIENTS_DIR" 2>/dev/null || true
    rm -rf /app/CLIENTS /app/master_mt5 2>/dev/null || true
    ln -sfn "$CLIENTS_DIR" /app/CLIENTS
    ln -sfn "$MASTER_MT5_DIR" /app/master_mt5
    echo "[+] Linked CLIENTS -> $CLIENTS_DIR"
    echo "[+] Linked master_mt5 -> $MASTER_MT5_DIR"
fi

# Cleanup handler on container shutdown
cleanup() {
    echo "[-] Shutting down MT5 worker..."
    kill -TERM "$WATCHDOG_PID" 2>/dev/null || true
    kill -TERM "$XVFB_PID" 2>/dev/null || true
    exit 0
}
trap cleanup SIGTERM SIGINT

# 3. Launch Worker Manager under Wine Windows Python
echo "[+] Starting Worker Manager..."
export PYTHONUNBUFFERED=1
wine python -u worker_manager.py "$@"
