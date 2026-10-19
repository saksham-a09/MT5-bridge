import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Set
from fastapi import WebSocket
from .db import (
    get_db, add_log, get_all_nodes, get_dashboard_summary,
    get_all_accounts, get_logs, get_all_copy_groups, get_copied_trades
)
from .config import settings
from .copier_engine import copier_engine

logger = logging.getLogger("HubScheduler")

class ConnectionManager:
    """Manages active WebSocket connections from web dashboards."""
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        dead = []
        payload = json.dumps(message)
        for conn in self.active_connections:
            try:
                await conn.send_text(payload)
            except Exception:
                dead.append(conn)
        for conn in dead:
            self.active_connections.discard(conn)

ws_manager = ConnectionManager()

def parse_iso(dt_str: str) -> datetime:
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return datetime.now(timezone.utc)

def run_heartbeat_and_balancing():
    """Checks for dead nodes and auto-balances active accounts."""
    now = datetime.now(timezone.utc)
    nodes = get_all_nodes()
    
    with get_db() as conn:
        # 1. Check node timeouts
        for node in nodes:
            node_id = node["node_id"]
            if node["status"] == "online" and node.get("last_heartbeat"):
                hb_time = parse_iso(node["last_heartbeat"])
                elapsed = (now - hb_time).total_seconds()
                if elapsed > settings.HEARTBEAT_TIMEOUT_SECONDS:
                    conn.execute("UPDATE worker_nodes SET status = 'offline' WHERE node_id = ?", (node_id,))
                    add_log(
                        f"Worker Node '{node['name']}' ({node_id}) timed out ({int(elapsed)}s since last heartbeat). Marked OFFLINE.",
                        level="WARNING",
                        source="SCHEDULER",
                        conn=conn
                    )

        # Refresh nodes list after timeout updates
        cursor = conn.execute("SELECT * FROM worker_nodes WHERE status = 'online'")
        online_nodes = [dict(r) for r in cursor.fetchall()]

        # 2. Check accounts needing assignment
        cursor = conn.execute("""
        SELECT a.login, a.target_node_id, a.assigned_node_id, w.status as assigned_status
        FROM accounts a
        LEFT JOIN worker_nodes w ON a.assigned_node_id = w.node_id
        WHERE a.status = 'active'
        """)
        accounts = [dict(r) for r in cursor.fetchall()]

        for acc in accounts:
            login = acc["login"]
            target = acc.get("target_node_id") or "auto"
            current_node = acc.get("assigned_node_id")
            assigned_status = acc.get("assigned_status")

            # Check if assignment needs change
            needs_reassign = False
            if not current_node:
                needs_reassign = True
            elif assigned_status != "online":
                needs_reassign = True
            elif target != "auto" and current_node != target:
                needs_reassign = True

            if needs_reassign:
                chosen_node_id = None
                if target != "auto":
                    # Manually pinned to a specific node
                    for n in online_nodes:
                        if n["node_id"] == target:
                            chosen_node_id = target
                            break
                else:
                    # Auto-balance: pick the online node with the most available slots
                    candidates = []
                    for n in online_nodes:
                        capacity = n.get("max_terminals", 25)
                        active = n.get("active_terminals", 0)
                        free_slots = max(0, capacity - active)
                        if free_slots > 0:
                            candidates.append((free_slots, n["node_id"], n["name"]))
                    
                    if candidates:
                        candidates.sort(key=lambda x: x[0], reverse=True)
                        chosen_node_id = candidates[0][1]

                if chosen_node_id and chosen_node_id != current_node:
                    conn.execute("UPDATE accounts SET assigned_node_id = ? WHERE login = ?", (chosen_node_id, login))
                    add_log(
                        f"Account {login} assigned to Worker Node '{chosen_node_id}'.",
                        level="INFO",
                        source="BALANCER",
                        conn=conn
                    )
                elif not chosen_node_id and current_node:
                    # Current node went down and no other online node has capacity
                    conn.execute("UPDATE accounts SET assigned_node_id = NULL WHERE login = ?", (login,))
                    add_log(
                        f"Account {login} unassigned: no online worker node available with free terminal capacity.",
                        level="WARNING",
                        source="BALANCER",
                        conn=conn
                    )

async def scheduler_loop():
    """Background loop that periodically maintains cluster health and broadcasts updates."""
    logger.info("Scheduler loop started.")
    while True:
        try:
            # Run heartbeat checking & balancing in a thread
            await asyncio.to_thread(run_heartbeat_and_balancing)

            # Run trade copier sync evaluation
            await asyncio.to_thread(copier_engine.sync_copy_groups)

            # Broadcast real-time update to WebSocket clients
            summary = await asyncio.to_thread(get_dashboard_summary)
            nodes = await asyncio.to_thread(get_all_nodes)
            accounts = await asyncio.to_thread(get_all_accounts)
            logs = await asyncio.to_thread(get_logs, 20)
            copy_groups = await asyncio.to_thread(get_all_copy_groups)
            copied_trades = await asyncio.to_thread(get_copied_trades, None, 30)

            await ws_manager.broadcast({
                "type": "TICK",
                "summary": summary,
                "nodes": nodes,
                "accounts": accounts,
                "logs": logs,
                "copy_groups": copy_groups,
                "copied_trades": copied_trades
            })
        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}")

        await asyncio.sleep(1)
