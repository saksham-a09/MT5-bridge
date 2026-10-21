# Docker Deployment Guide

This project contains containerization for the controller (backend and frontend) and worker nodes (Wine and MT5 on Linux).

---

## 1. Quick Start: Controller and Web Dashboard

To launch the controller (FastAPI) and the web dashboard (React and Nginx) on your server or VPS:

```bash
docker compose up -d --build
```

### Service Endpoints
- Web Dashboard: http://localhost (or http://YOUR_SERVER_IP on port 80 or 3000)
- API: http://localhost:8000
- Swagger Docs: http://localhost:8000/docs

### Services
1. **backend**:
   - Python 3.11 container running FastAPI and Uvicorn.
   - Automatically initializes the SQLite database with persistent storage in a Docker volume.
2. **frontend**:
   - Production bundle served with lightweight Nginx Alpine on port 3000.
   - Automatically proxies /api/ and /ws (WebSockets) to the backend.

---

## 2. Deploying a Worker Node in Docker (Linux VPS)

To run MT5 trading terminals inside Docker on a Linux VPS (Ubuntu, Debian, etc.):

### Step 1: Clone Repository and Pull Git LFS Binaries
```bash
# 1. Install Git LFS so large MT5 binaries (*.exe, *.dll) are downloaded instead of text pointers
sudo apt-get update && sudo apt-get install -y git-lfs

# 2. Clone repository and pull LFS objects
git clone <your-repo>
cd "MT5-bridge"
git lfs install
git lfs pull

# 3. Enter worker_node directory
cd worker_node
```

### Step 2: Configure Environment Variables
Edit `docker-compose.worker.yml` (or create a `.env` file in `worker_node/`):
```ini
HUB_URL=http://YOUR_SERVER_IP:8000
NODE_ID=vps-linux-frankfurt-01
NODE_NAME="Frankfurt Linux VPS"
NODE_API_KEY=mt5-cluster-secret-key-2026
MAX_TERMINALS=30
```

### Step 3: Launch Worker Container
```bash
docker compose -f docker-compose.worker.yml up -d --build
```

### Container Features
- Wine 64-bit/32-bit, Xvfb virtual display buffer, Windows Python 3.11, and MetaTrader 5.
- Automatically registers with the controller and streams live hardware stats (CPU, RAM, terminals).
- Mounts `./CLIENTS` to persist cloned MT5 instances on the host.

---

## 3. Common Docker Commands

### View Live Logs
```bash
# View controller logs
docker compose logs -f

# View specific service logs
docker compose logs -f backend
docker compose logs -f frontend

# View worker logs
docker compose -f worker_node/docker-compose.worker.yml logs -f
```

### Restart Services
```bash
docker compose restart
```

### Stop Services
```bash
# Stop controller and dashboard
docker compose down

# Stop worker
docker compose -f worker_node/docker-compose.worker.yml down
```

### Rebuild After Code Changes
```bash
docker compose up -d --build
```

---

## 4. Persistent Storage and Backups

- The database is safely stored in the `hub-db-data` Docker volume.
- To backup the database file directly:
  ```bash
  docker cp backend:/app/data/hub.db ./backup.db
  ```
- To restore a database:
  ```bash
  docker cp ./backup.db backend:/app/data/hub.db
  docker compose restart backend
  ```
