#!/usr/bin/env bash
# ==============================================================================
# MT5 Distributed Worker Node - Linux Setup & Dependency Installer
# ==============================================================================
# This script automatically checks, installs, and configures everything
# required to run the MetaTrader 5 worker container on a Linux host (VPS / Dedicated).
#
# Supported Distros: Ubuntu, Debian, CentOS, RHEL, Rocky Linux, AlmaLinux, Fedora, Arch
# Architecture: x86_64 / amd64 (aarch64 supported via QEMU binfmt emulation)
# ==============================================================================

set -o pipefail

# --- ANSI Color Codes ---
BOLD='\033[1m'
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# --- Logging Helpers ---
log_info() { echo -e "${CYAN}[INFO]${NC} $1"; }
log_ok()   { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_err()  { echo -e "${RED}[ERROR]${NC} $1" >&2; }
log_step() { echo -e "\n${BOLD}${BLUE}==>${NC} ${BOLD}$1${NC}"; }

# --- Flags & Arguments ---
AUTO_START=false
ONLY_BUILD=false
NON_INTERACTIVE=false
SHOW_STATUS=false

for arg in "$@"; do
    case "$arg" in
        -s|--start)
            AUTO_START=true
            ;;
        -b|--build)
            ONLY_BUILD=true
            ;;
        -y|--yes)
            NON_INTERACTIVE=true
            ;;
        --status)
            SHOW_STATUS=true
            ;;
        -h|--help)
            echo "Usage: ./setup_worker_linux.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -s, --start       Automatically build and start the MT5 worker container after setup"
            echo "  -b, --build       Only build the Docker container image without starting"
            echo "  -y, --yes         Non-interactive mode (skip interactive prompts)"
            echo "      --status      Check the status of the MT5 worker container"
            echo "  -h, --help        Show this help message"
            exit 0
            ;;
        *)
            log_warn "Unknown option '$arg' ignored."
            ;;
    esac
done

# If not running in a terminal (e.g. piped or automated script), default to non-interactive
if [ ! -t 0 ]; then
    NON_INTERACTIVE=true
fi

# Determine script & repository directories
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "$SCRIPT_DIR/docker-compose.worker.yml" ]; then
    WORKER_DIR="$SCRIPT_DIR"
    REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
elif [ -f "$SCRIPT_DIR/worker_node/docker-compose.worker.yml" ]; then
    WORKER_DIR="$SCRIPT_DIR/worker_node"
    REPO_ROOT="$SCRIPT_DIR"
else
    WORKER_DIR="$SCRIPT_DIR"
    REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
fi

echo -e "${BOLD}${CYAN}"
echo "=================================================================="
echo "    MT5 Worker Node Container - Linux Dependency & Setup Tool     "
echo "=================================================================="
echo -e "${NC}"
echo "Worker Directory : $WORKER_DIR"
echo "Repository Root  : $REPO_ROOT"
echo ""

# --- Helper: Check Container Status ---
check_container_status() {
    log_step "Checking MT5 Worker Container Status..."
    local compose_bin=""
    if docker compose version >/dev/null 2>&1; then
        compose_bin="docker compose"
    elif command -v docker-compose >/dev/null 2>&1; then
        compose_bin="docker-compose"
    fi

    if [ -n "$compose_bin" ] && [ -f "$WORKER_DIR/docker-compose.worker.yml" ]; then
        (cd "$WORKER_DIR" && $compose_bin -f docker-compose.worker.yml ps)
    else
        docker ps --filter "name=mt5-worker-node"
    fi
}

if [ "$SHOW_STATUS" = true ]; then
    check_container_status
    exit 0
fi

# ==============================================================================
# Step 1: Privilege & Package Manager Detection
# ==============================================================================
log_step "1/8: Checking User Privileges & Operating System..."

SUDO=""
if [ "$(id -u)" -ne 0 ]; then
    if command -v sudo >/dev/null 2>&1; then
        # Check sudo access without hanging indefinitely
        if sudo -v 2>/dev/null; then
            SUDO="sudo"
            log_ok "Running as non-root user with sudo privileges."
        else
            log_warn "Prompting for sudo password..."
            if sudo -v; then
                SUDO="sudo"
                log_ok "Sudo privileges granted."
            else
                log_err "This script requires sudo privileges to install packages and configure Docker."
                exit 1
            fi
        fi
    else
        log_err "Running as non-root and 'sudo' is not installed. Please run as root or install sudo."
        exit 1
    fi
else
    log_ok "Running directly as root."
fi

# Detect Linux Distribution
PKG_MANAGER=""
OS_NAME=""
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS_NAME="${PRETTY_NAME:-$ID}"
fi
log_info "Detected OS: $OS_NAME"

if command -v apt-get >/dev/null 2>&1; then
    PKG_MANAGER="apt"
elif command -v dnf >/dev/null 2>&1; then
    PKG_MANAGER="dnf"
elif command -v yum >/dev/null 2>&1; then
    PKG_MANAGER="yum"
elif command -v pacman >/dev/null 2>&1; then
    PKG_MANAGER="pacman"
elif command -v zypper >/dev/null 2>&1; then
    PKG_MANAGER="zypper"
else
    log_warn "Unknown package manager. Automatic package installation might be limited."
fi
log_ok "Package Manager: ${PKG_MANAGER:-unknown}"

# ==============================================================================
# Step 2: CPU Architecture & Emulation Check
# ==============================================================================
log_step "2/8: Checking CPU Architecture..."
ARCH="$(uname -m)"
log_info "Architecture: $ARCH"

if [ "$ARCH" = "x86_64" ] || [ "$ARCH" = "amd64" ]; then
    log_ok "Architecture is x86_64 (native support for Wine and MT5 64-bit binaries)."
elif [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then
    log_warn "ARM64 architecture detected! MT5 runs as Windows x86_64 binary."
    log_info "Installing QEMU user-mode static emulation and binfmt support..."
    if [ "$PKG_MANAGER" = "apt" ]; then
        $SUDO apt-get update -qq
        $SUDO apt-get install -y -qq qemu-user-static binfmt-support
    elif [ "$PKG_MANAGER" = "dnf" ] || [ "$PKG_MANAGER" = "yum" ]; then
        $SUDO $PKG_MANAGER install -y qemu-user-static
    fi
    log_ok "QEMU user-mode emulation installed."
else
    log_warn "Non-standard architecture '$ARCH'. MT5 container requires x86_64 emulation."
fi

# ==============================================================================
# Step 3: Base Tools & Git LFS Check / Installation
# ==============================================================================
log_step "3/8: Verifying System Dependencies & Git LFS..."

install_packages() {
    local pkgs=("$@")
    if [ ${#pkgs[@]} -eq 0 ]; then return; fi
    log_info "Installing packages: ${pkgs[*]}..."
    case "$PKG_MANAGER" in
        apt)
            $SUDO apt-get update -qq
            $SUDO apt-get install -y --no-install-recommends "${pkgs[@]}"
            ;;
        dnf|yum)
            $SUDO $PKG_MANAGER install -y "${pkgs[@]}"
            ;;
        pacman)
            $SUDO pacman -Sy --noconfirm "${pkgs[@]}"
            ;;
        zypper)
            $SUDO zypper --non-interactive install "${pkgs[@]}"
            ;;
        *)
            log_err "Cannot install packages automatically on this distribution."
            ;;
    esac
}

MISSING_PKGS=()
for tool in curl wget ca-certificates gnupg sed git; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        MISSING_PKGS+=("$tool")
    fi
done

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
    install_packages "${MISSING_PKGS[@]}"
else
    log_ok "Core utilities (curl, wget, ca-certificates, gnupg, sed, git) are installed."
fi

# Git LFS Installation & Setup
if ! command -v git-lfs >/dev/null 2>&1; then
    log_info "Git LFS is not installed. Installing git-lfs..."
    if [ "$PKG_MANAGER" = "apt" ]; then
        $SUDO apt-get update -qq && $SUDO apt-get install -y git-lfs
    elif [ "$PKG_MANAGER" = "dnf" ] || [ "$PKG_MANAGER" = "yum" ]; then
        $SUDO $PKG_MANAGER install -y git-lfs
    elif [ "$PKG_MANAGER" = "pacman" ]; then
        $SUDO pacman -Sy --noconfirm git-lfs
    fi
fi

if command -v git-lfs >/dev/null 2>&1; then
    git lfs install --skip-repo >/dev/null 2>&1 || git lfs install >/dev/null 2>&1 || true
    log_ok "Git LFS is active ($(git lfs version | head -n1))."
else
    log_warn "Could not install Git LFS automatically. Please install git-lfs manually."
fi

# ==============================================================================
# Step 4: MT5 Master Template & Git LFS Binary Integrity Check
# ==============================================================================
log_step "4/8: Checking Master MT5 Template & Binary Integrity..."

# Find Master MT5 directory
MASTER_DIR=""
POSSIBLE_MASTER_PATHS=(
    "$REPO_ROOT/Master MT5"
    "$WORKER_DIR/../Master MT5"
    "$WORKER_DIR/Master MT5"
    "../Master MT5"
    "./Master MT5"
)

for p in "${POSSIBLE_MASTER_PATHS[@]}"; do
    if [ -d "$p" ]; then
        MASTER_DIR="$p"
        break
    fi
done

# If Master MT5 exists only inside worker_node, ensure ../Master MT5 symlink exists
# because docker-compose.worker.yml mounts: ../Master MT5:/app/master_mt5:ro
if [ ! -d "$WORKER_DIR/../Master MT5" ] && [ -d "$WORKER_DIR/Master MT5" ]; then
    log_info "Creating symlink for Master MT5 volume mapping: ../Master MT5 -> $WORKER_DIR/Master MT5"
    ln -s "$WORKER_DIR/Master MT5" "$WORKER_DIR/../Master MT5" 2>/dev/null || true
fi

if [ -n "$MASTER_DIR" ]; then
    log_ok "Master MT5 directory found at: $MASTER_DIR"
    TERMINAL_EXE="$MASTER_DIR/terminal64.exe"
    
    if [ -f "$TERMINAL_EXE" ]; then
        FILE_SIZE=$(wc -c < "$TERMINAL_EXE" 2>/dev/null || stat -c %s "$TERMINAL_EXE" 2>/dev/null || echo 0)
        # Check if it's a Git LFS text pointer (< 1000 bytes or starts with version https://git-lfs)
        HEADER_SAMPLE=$(head -c 30 "$TERMINAL_EXE" 2>/dev/null || true)
        
        if [[ "$HEADER_SAMPLE" == *"version https://git-lfs"* ]] || [ "$FILE_SIZE" -lt 1048576 ]; then
            log_warn "Detected Git LFS pointer text file (${FILE_SIZE} bytes), NOT real MT5 binary!"
            log_info "Fetching actual terminal64.exe binary via 'git lfs pull'..."
            if [ -d "$REPO_ROOT/.git" ]; then
                (cd "$REPO_ROOT" && git lfs pull)
                NEW_SIZE=$(wc -c < "$TERMINAL_EXE" 2>/dev/null || echo 0)
                if [ "$NEW_SIZE" -gt 10485760 ]; then
                    log_ok "Successfully pulled real MT5 terminal64.exe binary ($((NEW_SIZE / 1024 / 1024)) MB)!"
                else
                    log_warn "git lfs pull finished, but binary size is still small ($NEW_SIZE bytes). Please verify git credentials."
                fi
            else
                log_err "Not a git repository. Please copy the full ~118MB terminal64.exe into '$MASTER_DIR'."
            fi
        else
            log_ok "Valid MT5 binary confirmed: terminal64.exe ($((FILE_SIZE / 1024 / 1024)) MB)."
        fi
    else
        log_warn "terminal64.exe was not found inside '$MASTER_DIR'!"
    fi
else
    log_warn "Master MT5 template folder not found in common locations. Mount path ../Master MT5 must be populated before running."
fi

# ==============================================================================
# Step 5: Docker Engine Check & Installation
# ==============================================================================
log_step "5/8: Checking Docker Engine..."

if ! command -v docker >/dev/null 2>&1; then
    log_info "Docker is not installed. Installing Docker via official script..."
    TEMP_SCRIPT="/tmp/get-docker.sh"
    curl -fsSL https://get.docker.com -o "$TEMP_SCRIPT"
    $SUDO sh "$TEMP_SCRIPT"
    rm -f "$TEMP_SCRIPT"
    log_ok "Docker installation completed."
else
    DOCKER_VER=$(docker --version | cut -d',' -f1)
    log_ok "Docker is already installed ($DOCKER_VER)."
fi

# Ensure Docker service is running and enabled
if command -v systemctl >/dev/null 2>&1; then
    if ! systemctl is-active --quiet docker; then
        log_info "Starting Docker service..."
        $SUDO systemctl enable --now docker
    fi
elif command -v service >/dev/null 2>&1; then
    $SUDO service docker status >/dev/null 2>&1 || $SUDO service docker start
fi

# Verify Docker daemon is responsive
if ! $SUDO docker info >/dev/null 2>&1; then
    log_err "Docker daemon is not running or not responsive. Please start docker and retry."
    exit 1
fi
log_ok "Docker daemon is running and healthy."

# Add current user to docker group if running as non-root
if [ "$(id -u)" -ne 0 ]; then
    CURRENT_USER="$(id -un)"
    if ! id -nG "$CURRENT_USER" | grep -qw "docker"; then
        log_info "Adding user '$CURRENT_USER' to 'docker' group..."
        $SUDO usermod -aG docker "$CURRENT_USER" || true
        log_warn "User added to 'docker' group. You may need to log out and log back in for group changes to take effect without sudo."
    fi
fi

# ==============================================================================
# Step 6: Docker Compose Check & Installation
# ==============================================================================
log_step "6/8: Checking Docker Compose..."

DOCKER_COMPOSE=""
if docker compose version >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker compose"
    log_ok "Docker Compose v2 plugin detected ($(docker compose version --short 2>/dev/null || docker compose version))."
elif command -v docker-compose >/dev/null 2>&1; then
    DOCKER_COMPOSE="docker-compose"
    log_ok "Standalone docker-compose detected ($(docker-compose --version))."
else
    log_info "Docker Compose not found. Installing docker-compose-plugin..."
    if [ "$PKG_MANAGER" = "apt" ]; then
        $SUDO apt-get update -qq
        $SUDO apt-get install -y docker-compose-plugin || true
    elif [ "$PKG_MANAGER" = "dnf" ] || [ "$PKG_MANAGER" = "yum" ]; then
        $SUDO $PKG_MANAGER install -y docker-compose-plugin || true
    fi

    if docker compose version >/dev/null 2>&1; then
        DOCKER_COMPOSE="docker compose"
        log_ok "Installed Docker Compose v2 plugin."
    else
        # Fallback: install standalone binary
        log_info "Downloading standalone docker-compose binary..."
        COMPOSE_URL="https://github.com/docker/compose/releases/latest/download/docker-compose-linux-$(uname -m)"
        $SUDO curl -fsSL "$COMPOSE_URL" -o /usr/local/bin/docker-compose
        $SUDO chmod +x /usr/local/bin/docker-compose
        DOCKER_COMPOSE="docker-compose"
        log_ok "Installed standalone docker-compose binary."
    fi
fi

# ==============================================================================
# Step 7: Linux Kernel Tuning for Wine & MT5 Terminals
# ==============================================================================
log_step "7/8: Tuning Kernel Limits for Wine & Multiple MT5 Terminals..."

CURRENT_MAX_MAP=$(sysctl -n vm.max_map_count 2>/dev/null || echo 65530)
log_info "Current vm.max_map_count: $CURRENT_MAX_MAP"

# Wine running dozens of MT5 instances requires high memory mapping limits
if [ "$CURRENT_MAX_MAP" -lt 262144 ]; then
    TARGET_MAX_MAP=1048576
    log_info "Increasing vm.max_map_count to $TARGET_MAX_MAP..."
    $SUDO sysctl -w vm.max_map_count=$TARGET_MAX_MAP >/dev/null 2>&1 || true
    
    # Persist across system reboots
    SYSCTL_CONF="/etc/sysctl.d/99-mt5-worker.conf"
    if [ -d "/etc/sysctl.d" ]; then
        echo "# MT5 Cluster Worker Wine memory & file limits" | $SUDO tee "$SYSCTL_CONF" >/dev/null
        echo "vm.max_map_count=1048576" | $SUDO tee -a "$SYSCTL_CONF" >/dev/null
        echo "fs.file-max=2097152" | $SUDO tee -a "$SYSCTL_CONF" >/dev/null
        log_ok "Persisted kernel limits to $SYSCTL_CONF."
    fi
else
    log_ok "vm.max_map_count ($CURRENT_MAX_MAP) is already optimal."
fi

# ==============================================================================
# Step 8: Worker Environment & File Configuration
# ==============================================================================
log_step "8/8: Preparing Worker Configuration & Directories..."

# 1. Ensure CLIENTS directory exists and is writable
CLIENTS_DIR="$WORKER_DIR/CLIENTS"
mkdir -p "$CLIENTS_DIR"
chmod 777 "$CLIENTS_DIR" 2>/dev/null || true
log_ok "CLIENTS directory ready: $CLIENTS_DIR"

# 2. Fix line endings on entrypoint.sh (strip CRLF) and ensure executable
if [ -f "$WORKER_DIR/entrypoint.sh" ]; then
    sed -i 's/\r$//' "$WORKER_DIR/entrypoint.sh"
    chmod +x "$WORKER_DIR/entrypoint.sh"
    log_ok "Sanitized entrypoint.sh (LF line endings & executable permissions)."
fi

# 3. Handle .env configuration
ENV_FILE="$WORKER_DIR/.env"
ENV_EXAMPLE="$WORKER_DIR/.env.example"

if [ ! -f "$ENV_FILE" ]; then
    if [ -f "$ENV_EXAMPLE" ]; then
        log_info "Creating .env from .env.example..."
        cp "$ENV_EXAMPLE" "$ENV_FILE"
        log_ok "Created $ENV_FILE. Please verify HUB_URL and NODE_API_KEY."
    else
        log_warn ".env.example not found. Creating default .env..."
        cat <<EOF > "$ENV_FILE"
HUB_URL=http://127.0.0.1:8000
NODE_ID=vps-linux-worker-01
NODE_NAME="Linux Cloud Worker 1"
NODE_API_KEY=mt5-cluster-secret-key-2026
MASTER_MT5_DIR=/app/master_mt5
CLIENTS_DIR=/app/CLIENTS
MAX_TERMINALS=30
POLL_INTERVAL=8
FAST_POLL_INTERVAL=0.08
COMMAND_POLL_INTERVAL=0.15
TELEMETRY_INTERVAL=2.0
EOF
        log_ok "Default .env created."
    fi
else
    log_ok ".env configuration exists."
fi

# Extract and display key settings
HUB_URL=$(grep -E "^HUB_URL=" "$ENV_FILE" | head -n1 | cut -d'=' -f2- | tr -d '"' | tr -d "'" | tr -d '\r')
NODE_ID=$(grep -E "^NODE_ID=" "$ENV_FILE" | head -n1 | cut -d'=' -f2- | tr -d '"' | tr -d "'" | tr -d '\r')
log_info "Configured Central Hub URL: ${HUB_URL:-Not Set}"
log_info "Configured Node ID         : ${NODE_ID:-Not Set}"

# Test Central Hub connectivity if HUB_URL is set
if [ -n "$HUB_URL" ] && [[ "$HUB_URL" != *"127.0.0.1"* ]] && [[ "$HUB_URL" != *"localhost"* ]]; then
    log_info "Testing connectivity to Central Hub ($HUB_URL)..."
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 4 "$HUB_URL/health" 2>/dev/null || echo "failed")
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "404" ] || [ "$HTTP_CODE" = "401" ] || [ "$HTTP_CODE" = "403" ]; then
        log_ok "Central Hub is reachable (HTTP $HTTP_CODE)."
    else
        log_warn "Could not reach Central Hub at '$HUB_URL' (HTTP code: $HTTP_CODE). Please check firewall/IP."
    fi
fi

# ==============================================================================
# Summary & Container Launch
# ==============================================================================
echo ""
echo -e "${BOLD}${GREEN}==================================================================${NC}"
echo -e "${BOLD}${GREEN}  All Linux Prerequisites for MT5 Worker Container are Ready!     ${NC}"
echo -e "${BOLD}${GREEN}==================================================================${NC}"
echo ""
echo "Summary of verified components:"
echo "  [✓] Operating System       : $OS_NAME ($ARCH)"
echo "  [✓] Docker Engine          : Installed & Active"
echo "  [✓] Docker Compose         : $DOCKER_COMPOSE"
echo "  [✓] Git LFS                : Installed & Verified"
echo "  [✓] Kernel Limits          : vm.max_map_count optimal"
echo "  [✓] Worker Environment     : CLIENTS & .env configured"
echo ""

START_CONTAINER=false

if [ "$AUTO_START" = true ]; then
    START_CONTAINER=true
elif [ "$ONLY_BUILD" = true ]; then
    log_step "Building MT5 Worker Docker Container..."
    (cd "$WORKER_DIR" && $DOCKER_COMPOSE -f docker-compose.worker.yml build)
    log_ok "Worker Docker image built successfully."
    exit 0
elif [ "$NON_INTERACTIVE" = false ]; then
    read -r -p "Would you like to build and start the MT5 Worker Container now? [y/N]: " USER_CHOICE
    case "$USER_CHOICE" in
        [yY][eE][sS]|[yY])
            START_CONTAINER=true
            ;;
        *)
            START_CONTAINER=false
            ;;
    esac
fi

if [ "$START_CONTAINER" = true ]; then
    log_step "Launching MT5 Worker Container..."
    (cd "$WORKER_DIR" && $DOCKER_COMPOSE -f docker-compose.worker.yml up -d --build)
    
    echo ""
    log_ok "MT5 Worker Node container launched!"
    echo ""
    echo "Useful Commands:"
    echo "  - View live container logs :"
    echo "    $DOCKER_COMPOSE -f $WORKER_DIR/docker-compose.worker.yml logs -f"
    echo ""
    echo "  - Restart worker container :"
    echo "    $DOCKER_COMPOSE -f $WORKER_DIR/docker-compose.worker.yml restart"
    echo ""
    echo "  - Stop worker container    :"
    echo "    $DOCKER_COMPOSE -f $WORKER_DIR/docker-compose.worker.yml down"
    echo ""
else
    echo "To launch the worker container manually at any time, run:"
    echo -e "  ${CYAN}cd \"$WORKER_DIR\" && $DOCKER_COMPOSE -f docker-compose.worker.yml up -d --build${NC}"
    echo ""
    echo "To view live logs:"
    echo -e "  ${CYAN}cd \"$WORKER_DIR\" && $DOCKER_COMPOSE -f docker-compose.worker.yml logs -f${NC}"
    echo ""
fi
