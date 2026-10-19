import os
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from .config import settings
from .db import init_db, add_log, get_all_nodes, register_node
from .scheduler import scheduler_loop, ws_manager
from .api_accounts import router as accounts_router
from .api_nodes import router as nodes_router
from .api_dashboard import router as dashboard_router
from .api_copier import router as copier_router

scheduler_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler_task
    # 1. Initialize SQLite Database
    init_db()
    add_log(f"{settings.APP_NAME} started on http://{settings.HOST}:{settings.PORT}", source="HUB")

    # 2. Seed a default Local Node if none exist
    nodes = get_all_nodes()
    if not nodes:
        register_node(
            node_id="local-node-1",
            name="Primary Local Node",
            api_key="local_secret_key",
            ip_address="127.0.0.1",
            max_terminals=20,
            os_info="Local Host (Windows)"
        )
        add_log("Created initial 'local-node-1' worker manager node.", source="HUB")

    # 3. Ensure user requested accounts are active and clean up placeholder demo accounts
    from .db import create_account, delete_account
    for dummy_login in [25500730, 25506235, 26196355, 26196352, 26196348]:
        delete_account(dummy_login)

    user_accounts = [
        {"login": 26302967, "password": "P6c&Lcju", "server": "VantageMarkets-Demo", "name": "Vantage Account 26302967"},
        {"login": 26302966, "password": "*tJ#F*5X", "server": "VantageMarkets-Demo", "name": "Vantage Account 26302966"},
    ]
    for acc in user_accounts:
        create_account(
            login=acc["login"],
            password=acc["password"],
            server=acc["server"],
            name=acc["name"],
            target_node_id="auto",
            expert="",
            symbol="XAUUSD",
            timeframe="M1"
        )

    # 4. Seed a default Copy Trading Group if none exist
    from .db import get_all_copy_groups, create_copy_group, add_slave_to_group
    groups = get_all_copy_groups()
    if not groups:
        new_grp = create_copy_group(
            name="Vantage Demo Copier (Master -> Slave)",
            master_login=26302967,
            risk_type="multiplier",
            multiplier=1.0,
            max_slippage_points=20,
            copy_sl_tp=True,
            copy_pending_orders=True
        )
        if new_grp:
            add_slave_to_group(new_grp["id"], 26302966)
            add_log(f"Initialized default Copy Trading Group #{new_grp['id']} (Master: 26302967 -> Slave: 26302966)", source="COPIER")

    # 5. Start background health, trade copier and balancing scheduler
    scheduler_task = asyncio.create_task(scheduler_loop())

    yield

    # Shutdown
    if scheduler_task:
        scheduler_task.cancel()
    add_log("Hub server shutting down.", source="HUB")

app = FastAPI(
    title=settings.APP_NAME,
    description="Scalable Multi-Hardware MetaTrader 5 Terminal Cluster Manager & Dashboard",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(dashboard_router)
app.include_router(accounts_router)
app.include_router(nodes_router)
app.include_router(copier_router)

# WebSocket Endpoints for Live Dashboard updates
@app.websocket("/ws")
@app.websocket("/ws/dashboard")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            # Keep-alive receive
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)

# Frontend Static Assets Serving
frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists() and (frontend_dist / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dist / "assets")), name="assets")
    
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(frontend_dist / "index.html")
else:
    @app.get("/")
    def index_fallback():
        return {
            "name": settings.APP_NAME,
            "status": "online",
            "docs": "/docs",
            "endpoints": {
                "dashboard_stats": "/api/dashboard/stats",
                "accounts": "/api/accounts",
                "worker_nodes": "/api/nodes"
            }
        }
