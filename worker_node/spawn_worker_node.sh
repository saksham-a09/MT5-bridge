#!/bin/bash
set -e

# ==============================================================================
# MT5 Multi-Container Worker Node Launcher
# Allows launching as many isolated MT5 worker containers as you want on one host
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARENT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Load default config from .env if present
if [ -f "${SCRIPT_DIR}/.env" ]; then
    set -a
    source "${SCRIPT_DIR}/.env"
    set +a
fi

NODE_ID="$1"
NODE_NAME="$2"
MAX_TERMINALS="$3"
HUB_URL_OVERRIDE="$4"

if [ -z "$NODE_ID" ]; then
    echo "Usage: $0 <NODE_ID> [NODE_NAME] [MAX_TERMINALS] [HUB_URL]"
    echo ""
    echo "Examples:"
    echo "  $0 maws-1 \"mohit-aws-1\" 25"
    echo "  $0 maws-2 \"mohit-aws-2\" 25"
    echo "  $0 maws-3 \"mohit-aws-3\" 30"
    exit 1
fi

NODE_NAME="${NODE_NAME:-Node-${NODE_ID}}"
MAX_TERMINALS="${MAX_TERMINALS:-${MAX_TERMINALS:-25}}"
HUB_URL="${HUB_URL_OVERRIDE:-${HUB_URL:-http://34.131.201.122:8000}}"
NODE_API_KEY="${NODE_API_KEY:-node_token_d0a403bdcc7c}"
MASTER_MT5_DIR="${MASTER_MT5_DIR:-/app_data/Master MT5}"
CLIENTS_DIR="/app_data/worker_node/CLIENTS_${NODE_ID}"
CONTAINER_NAME="mt5-worker-node-${NODE_ID}"
IMAGE_NAME="worker_node-worker"

echo "=========================================================="
echo " Launching MT5 Worker Container: ${CONTAINER_NAME}"
echo "=========================================================="
echo "  Node ID:         ${NODE_ID}"
echo "  Node Name:       ${NODE_NAME}"
echo "  Hub URL:         ${HUB_URL}"
echo "  Max Terminals:   ${MAX_TERMINALS}"
echo "  Clients Dir:     ${CLIENTS_DIR}"
echo "  Shared App Data: ${PARENT_DIR}"
echo "=========================================================="

# Ensure host clone directory exists
HOST_CLIENTS_DIR="${PARENT_DIR}/worker_node/CLIENTS_${NODE_ID}"
mkdir -p "${HOST_CLIENTS_DIR}" 2>/dev/null || true

# Check if image exists, build if missing
if ! docker image inspect "${IMAGE_NAME}" >/dev/null 2>&1; then
    echo "[+] Building worker image '${IMAGE_NAME}'..."
    docker build -t "${IMAGE_NAME}" -f "${SCRIPT_DIR}/Dockerfile" "${SCRIPT_DIR}"
fi

# Stop and remove existing container with the same name if exists
if docker ps -a --format '{{.Names}}' | grep -Eq "^${CONTAINER_NAME}\$"; then
    echo "[*] Removing existing container '${CONTAINER_NAME}'..."
    docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
fi

# Launch container with host networking, isolated IPC, log caps, and dynamic DISPLAY
docker run -d \
    --name "${CONTAINER_NAME}" \
    --restart unless-stopped \
    --network host \
    --ipc host \
    --log-opt max-size=50m \
    --log-opt max-file=3 \
    -v "${PARENT_DIR}:/app_data" \
    -e "HUB_URL=${HUB_URL}" \
    -e "NODE_ID=${NODE_ID}" \
    -e "NODE_NAME=${NODE_NAME}" \
    -e "NODE_API_KEY=${NODE_API_KEY}" \
    -e "MASTER_MT5_DIR=${MASTER_MT5_DIR}" \
    -e "CLIENTS_DIR=${CLIENTS_DIR}" \
    -e "MAX_TERMINALS=${MAX_TERMINALS}" \
    -e "POLL_INTERVAL=8" \
    -e "FAST_POLL_INTERVAL=0.08" \
    -e "COMMAND_POLL_INTERVAL=0.15" \
    -e "TELEMETRY_INTERVAL=2.0" \
    -e "SPAWN_STAGGER_DELAY=6.0" \
    -e "SPAWN_TIMEOUT=35.0" \
    "${IMAGE_NAME}"

echo ""
echo "[✓] Container '${CONTAINER_NAME}' successfully launched!"
echo "Check live logs with: docker logs -f ${CONTAINER_NAME}"
