# MT5 Distributed Terminal Hub & Cluster Manager

A scalable, multi-hardware MetaTrader 5 terminal cluster management platform with a real-time web dashboard.

This system takes the proven worker architecture from **MT5 Remote API** (portable directory cloning, case-preserving configuration generation, aggressive chart clearing for low-RAM footprint, and API IPC binding) and transforms it into a distributed, multi-hardware cluster capable of running dozens or hundreds of terminals across multiple VPSs or local workstations.

---

## Architecture Overview

```mermaid
graph TB
    subgraph Central Hub ["Central Controller Hub (FastAPI + SQLite + WebSocket)"]
        API[FastAPI Endpoints]
        DB[(SQLite WAL Database)]
        SCHED[Auto-Balancer & Health Monitor]
        WS[Live WebSocket Broadcaster]
    end

    subgraph Dashboard ["Modern Web Dashboard (React + Vite)"]
        UI[Glassmorphism UI]
        STATS[Combined Balance & Equity]
        NODES_VIEW[Hardware Cluster Gauges]
        ACCOUNTS_VIEW[Account Table & Live Orders]
    end

    subgraph Node1 ["Hardware Node 1 (Local PC / VPS 1)"]
        WM1[Worker Manager 1]
        T1[MT5 Clone 25500730]
        T2[MT5 Clone 25506235]
    end

    subgraph Node2 ["Hardware Node 2 (New Remote VPS)"]
        WM2[Worker Manager 2]
        T3[MT5 Clone 25509911]
        T4[MT5 Clone 25509912]
    end

    Dashboard <-->|WebSocket / REST| Central Hub
    WM1 <-->|Heartbeats & Telemetry| Central Hub
    WM2 <-->|Heartbeats & Telemetry| Central Hub
    WM1 -->|Subprocesses| T1
    WM1 -->|Subprocesses| T2
    WM2 -->|Subprocesses| T3
    WM2 -->|Subprocesses| T4
```

---

## Key Features

### 1. Proven MT5 Worker Engine (from `MT5 Remote API`)
- **Master Directory Cloning**: Automatically creates isolated portable environments (`clone_{login}`) for each account from your master template.
- **Microscopic Memory Footprint**: Cleans all chart profiles (`.chr` files) in `MQL5/Profiles/Charts/` and `Profiles/Charts/` before launch, avoiding GPU/CPU rendering overhead so a single machine can run dozens of terminals.
- **Case-Preserving Config Generation**: Generates `config.ini` directly from credentials and optional startup EA/symbol/period.
- **Portable Launch**: Runs `terminal64.exe /portable /config:config.ini`.
- **Python IPC Binding**: Connects via `MetaTrader5` Python package with retries and timeout handling.
- **Telemetry Extraction**: Live balance, equity, margin, free margin, margin level, ping, and all open positions.
- **Process Supervision**: Detects process terminations or broker disconnects; auto-restarts terminals after consecutive failures.

### 2. Multi-Hardware Horizontal Scaling
- Add worker managers on **new hardware** (VPS, dedicated server, or local PC) with zero configuration friction.
- Each worker manager registers its hardware specs (CPU cores, RAM total, capacity limit).
- Sends periodic heartbeats with live CPU% and RAM% loads.
- **Auto-Load Balancer**: When new accounts are added, the Central Hub automatically assigns them to the online node with the most available capacity.
- **Pinning Support**: Manually pin high-priority accounts to specific hardware nodes if desired.

### 3. Real-Time Web Dashboard
- **Obsidian Dark Glassmorphism Design**: High-density, responsive control center with modern typography (Outfit & JetBrains Mono).
- **Combined Financials**: Live total balance, total equity, and floating P/L across all connected accounts.
- **Hardware Cluster Cards**: Real-time CPU and RAM usage bars, active terminals count vs capacity for every VPS.
- **Accounts Control Table**:
  - Filter by status (All, Active, Connected, Stopped).
  - Search by login, broker name, or server.
  - One-click Start, Stop, and Restart terminal controls.
- **Account Detail Modal**: Full view of live open positions (ticket, symbol, type, lots, open price, current price, profit, swap).
- **Add Worker Manager Guide**: Interactive modal providing a pre-configured `.env` and instructions to scale to new hardware.
- **Activity Log Drawer**: Live streaming cluster events (assignments, heartbeats, terminal restarts).

### 4. Ultra-Low Latency Distributed Trade Copier
- **Master & Slave Copy Groups**: Create custom copy trading groups linking 1 Master terminal to N Slave terminals across local or distributed VPS hardware.
- **Dynamic Lot Sizing Strategies**:
  - `multiplier`: Scales master volume by a custom factor (e.g. 1.0x, 0.5x, 2.0x).
  - `equity_ratio`: Automatically calculates proportional volume based on `(slave_equity / master_equity)`.
  - `balance_ratio`: Proportional to account balances.
  - `fixed_lot`: Strict fixed lot allocation (e.g. 0.01 lots).
- **Sub-100ms Mirroring Engine**:
  - Worker processes monitor positions on a 400ms cycle and process execution queues in under 50ms.
  - Broker filling mode auto-negotiation (`ORDER_FILLING_IOC` -> `ORDER_FILLING_FOK` -> `ORDER_FILLING_RETURN`) prevents `INVALID_FILL` rejections.
  - Normalized to symbol volume step, volume min, and volume max.
- **Full Trade Lifecycle Synchronization**:
  - **New Orders**: Instant replication with order tagging (`C:{master_ticket}`).
  - **Modifications**: Tracks Master SL/TP adjustments and synchronizes Slaves immediately.
  - **Closures**: Master close events trigger immediate market closes on Slaves with profit tracking.
- **Live Copied Trades Audit Table**: Real-time record of every copied order, execution latency in milliseconds, slippage points, and profits.

---

## Quick Start

### 1. Start the Central Hub
```powershell
cd backend
python run_server.py
```
*The Central Hub will start on `http://localhost:8000` and automatically serve the built web dashboard.*

### 2. Start the Local Worker Manager
```powershell
cd worker_node
python worker_manager.py
```
*Or double-click `start_worker.bat`.*

### 3. Open the Dashboard
Open your browser and navigate to:
```
http://localhost:8000
```
Interactive API docs are available at `http://localhost:8000/docs`.

---

## Scaling to New Hardware

To add worker capacity on a new Windows VPS or machine:

1. Copy the `worker_node` folder to the target machine.
2. In `worker_node/.env`, set:
   ```env
   HUB_URL=http://YOUR_HUB_IP:8000
   NODE_ID=vps-frankfurt-01
   NODE_NAME="Frankfurt VPS 1"
   NODE_API_KEY=local_secret_key
   MASTER_MT5_DIR=C:\MT5_Master
   MAX_TERMINALS=30
   ```
3. Run `start_worker.bat` or `python worker_manager.py`.

The Central Hub will immediately recognize the new hardware, display it in the cluster dashboard, and begin load-balancing terminals to it!
