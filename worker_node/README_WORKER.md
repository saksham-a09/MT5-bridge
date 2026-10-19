# MT5 Distributed Worker Manager

This is the lightweight worker manager node that runs on your trading hardware (local PC, Windows VPS, dedicated server, or Linux Wine instance).

It autonomously connects to your Central Hub, manages portable MT5 terminal instances, syncs telemetry (balance, equity, margins, open trades), and keeps accounts alive with automatic crash recovery.

---

## Deploying to New Hardware (VPS / Physical PC)

### Step 1: Copy this `worker_node` Folder
Copy or git clone this `worker_node` folder to your target hardware machine.

### Step 2: Ensure Prerequisites
- **Windows 10 / 11 / Windows Server** (or Linux with Wine + Xvfb)
- **Python 3.9+ 64-bit** (Make sure "Add Python to PATH" was checked during installation)
- **MetaTrader 5 Master Template Folder**:
  - Install MT5 once on the machine.
  - The folder should contain `terminal64.exe` (e.g. `C:\MT5_Master` or `C:\Program Files\MetaTrader 5`).

### Step 3: Configure `.env`
Edit the `.env` file on the new hardware:
```env
# URL of your central Hub server (e.g. your main server's public IP or domain)
HUB_URL=http://YOUR_HUB_IP:8000

# Unique identifier for this hardware node
NODE_ID=vps-frankfurt-01
NODE_NAME="Frankfurt VPS #1"
NODE_API_KEY=your_cluster_secret_key

# Path to the master MT5 folder on this hardware
MASTER_MT5_DIR=C:\MT5_Master

# Local directory where cloned user instances will run
CLIENTS_DIR=CLIENTS

# Max MT5 terminals this machine can comfortably handle (e.g., 20-40 based on RAM)
MAX_TERMINALS=30
POLL_INTERVAL=8
```

### Step 4: Install Dependencies & Run
Open PowerShell or Command Prompt in this folder:
```powershell
pip install -r requirements.txt
python worker_manager.py
```
Or simply double-click `start_worker.bat`!

---

## How It Works:
1. **Heartbeat & Telemetry**:
   - The worker manager reports its CPU%, RAM%, and active terminal count to the Central Hub every 10 seconds.
2. **Auto-Cloning & Low-RAM Execution**:
   - For each account assigned by the Central Hub, the worker manager clones the template MT5 into an isolated folder `CLIENTS/clone_{login}`.
   - Clears chart profiles (`.chr` files) so terminals consume virtually zero GPU/CPU rendering resources.
   - Starts MT5 in portable mode: `terminal64.exe /portable /config:config.ini`.
3. **Telemetry Streaming**:
   - Streams live balance, equity, margin, margin level, and all open positions back to the Central Hub dashboard.
4. **Resilience & Auto-Recovery**:
   - If a terminal closes unexpectedly or disconnects from the broker for several cycles, the worker manager automatically restarts it cleanly.
