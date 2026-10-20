# 🐳 Docker Deployment Guide: MT5 Distributed Bridge & Cluster

This project contains complete containerization for both the **Central Controller Hub (Backend & Frontend)** and **Worker Nodes (Wine + MT5 on Linux)**.

---

## 1. Quick Start: Central Hub & Web Dashboard

To launch the Central Controller Hub (FastAPI) and the Web Dashboard (React + Nginx) on your main server or VPS:

```bash
docker compose up -d --build
```

That's it! 

### Service Endpoints:
- **Web Dashboard**: [http://localhost](http://localhost) (or `http://YOUR_SERVER_IP` on standard port 80 / port 3000)
- **Central API Hub**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### What this runs:
1. **`mt5-hub-backend`**:
   - Python 3.11 container running FastAPI + Uvicorn.
   - Automatically initializes the SQLite database with persistent storage in a Docker volume (`hub-db-data`).
2. **`mt5-hub-frontend`**:
   - Multi-stage build producing an optimized production bundle.
   - Served with lightweight Nginx Alpine on port 3000.
   - Automatically proxies `/api/` and `/ws` (WebSockets) to the backend.

---

## 2. Deploying a Worker Node in Docker (Linux VPS)

If you have a Linux VPS (Ubuntu, Debian, etc.) and want to run MT5 trading terminals inside Docker:

### Step 1: Copy `worker_node` to the VPS
```bash
git clone <your-repo>
cd "MT5 bridge/worker_node"
```

### Step 2: Configure Environment Variables
Edit `docker-compose.worker.yml` (or create a `.env` file in `worker_node/`):
```ini
HUB_URL=http://YOUR_CENTRAL_HUB_IP:8000
NODE_ID=vps-linux-frankfurt-01
NODE_NAME="Frankfurt Linux VPS"
NODE_API_KEY=mt5-cluster-secret-key-2026
MAX_TERMINALS=30
```

### Step 3: Launch Worker Container
```bash
docker compose -f docker-compose.worker.yml up -d --build
```

### What this container does:
- Encapsulates **Wine 64-bit/32-bit**, **Xvfb virtual display buffer**, **Windows-native Python 3.11**, and **MetaTrader5**.
- Automatically registers with your Central Hub and begins streaming live hardware stats (CPU, RAM, terminals).
- Mounts `./CLIENTS` to persist cloned MT5 instances on the host.

---

## 3. Common Docker Commands

### View Live Logs:
```bash
# View Central Hub logs
docker compose logs -f

# View specific service logs
docker compose logs -f backend
docker compose logs -f frontend

# View worker logs
docker compose -f worker_node/docker-compose.worker.yml logs -f
```

### Restart Services:
```bash
docker compose restart
```

### Stop Services:
```bash
# Stop Hub & Dashboard (keeps database safe)
docker compose down

# Stop Worker
docker compose -f worker_node/docker-compose.worker.yml down
```

### Rebuild After Code Changes:
```bash
docker compose up -d --build
```

---

## 4. Persistent Storage & Backups

- The Central Hub database is safely stored in the `hub-db-data` Docker volume.
- To backup the database file directly:
  ```bash
  docker cp mt5-hub-backend:/app/data/hub.db ./backup_hub.db
  ```
- To restore a database:
  ```bash
  docker cp ./backup_hub.db mt5-hub-backend:/app/data/hub.db
  docker compose restart backend
  ```
