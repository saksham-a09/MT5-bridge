#!/usr/bin/env bash
# Forwarding runner for MT5 Worker Linux Setup & Dependency Installer
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "$SCRIPT_DIR/worker_node/setup_worker_linux.sh" "$@"
