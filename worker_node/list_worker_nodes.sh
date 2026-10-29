#!/bin/bash

# ==============================================================================
# Lists all running and stopped MT5 worker containers
# ==============================================================================

echo "=========================================================================================================="
echo " Active MT5 Worker Node Containers"
echo "=========================================================================================================="
docker ps -a --filter "name=mt5-worker-node" --format "table {{.Names}}\t{{.Status}}\t{{.RunningFor}}\t{{.ID}}"

echo ""
echo "X11 Virtual Displays Active:"
if [ -f /proc/net/unix ]; then
    grep -o "@*/tmp/\.X11-unix/X[0-9]*" /proc/net/unix | sort -u || echo "None"
fi
