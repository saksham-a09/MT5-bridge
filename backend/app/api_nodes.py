import uuid
from fastapi import APIRouter, HTTPException, Header, Request, Query
from typing import Optional
from .schemas import NodeRegister, NodeHeartbeat, BatchTelemetry
from .db import (
    get_all_nodes, get_node_by_id, register_node, delete_node,
    update_node_heartbeat, get_assigned_accounts_for_node,
    update_account_telemetry, add_log, get_pending_node_commands,
    complete_node_command
)
from .config import settings
from .copier_engine import copier_engine

router = APIRouter(prefix="/api/nodes", tags=["Worker Nodes"])

@router.get("")
def list_nodes():
    return {
        "success": True,
        "nodes": get_all_nodes()
    }

@router.post("/register")
def register_worker_node(payload: NodeRegister, request: Request):
    client_ip = payload.ip_address or (request.client.host if request.client else "")
    node = register_node(
        node_id=payload.node_id,
        name=payload.name,
        api_key=payload.api_key,
        ip_address=client_ip,
        max_terminals=payload.max_terminals or 25,
        os_info=payload.os_info or "Windows / Wine"
    )
    return {
        "success": True,
        "message": f"Worker Node '{payload.name}' registered successfully.",
        "node": node
    }

@router.delete("/{node_id}")
def remove_node(node_id: str):
    node = get_node_by_id(node_id)
    if not node:
        raise HTTPException(status_code=404, detail="Worker Node not found")
    delete_node(node_id)
    return {
        "success": True,
        "message": f"Worker Node '{node_id}' removed."
    }

@router.post("/{node_id}/heartbeat")
def node_heartbeat(node_id: str, payload: NodeHeartbeat, request: Request, x_node_api_key: Optional[str] = Header(None)):
    node = get_node_by_id(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Worker Node '{node_id}' is not registered.")
    
    # Optional auth check
    if x_node_api_key and node["api_key"] and x_node_api_key != node["api_key"]:
        raise HTTPException(status_code=401, detail="Invalid node API key")
        
    client_ip = payload.ip_address or (request.client.host if request.client else "")
    updated = update_node_heartbeat(
        node_id=node_id,
        cpu_percent=payload.cpu_percent,
        ram_percent=payload.ram_percent,
        ram_used_mb=payload.ram_used_mb,
        ram_total_mb=payload.ram_total_mb,
        active_terminals=payload.active_terminals,
        ip_address=client_ip
    )
    return {
        "success": updated,
        "status": "online"
    }

@router.get("/{node_id}/accounts")
def get_node_assigned_accounts(node_id: str, x_node_api_key: Optional[str] = Header(None)):
    node = get_node_by_id(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Worker Node '{node_id}' not found.")
        
    if x_node_api_key and node["api_key"] and x_node_api_key != node["api_key"]:
        raise HTTPException(status_code=401, detail="Invalid node API key")
        
    accounts = get_assigned_accounts_for_node(node_id)
    return {
        "success": True,
        "node_id": node_id,
        "accounts": accounts
    }

@router.post("/{node_id}/telemetry")
def submit_node_telemetry(node_id: str, payload: BatchTelemetry, x_node_api_key: Optional[str] = Header(None)):
    node = get_node_by_id(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Worker Node '{node_id}' not found.")
        
    if x_node_api_key and node["api_key"] and x_node_api_key != node["api_key"]:
        raise HTTPException(status_code=401, detail="Invalid node API key")

    count = 0
    for term in payload.terminals:
        update_account_telemetry(term.login, term.model_dump())
        count += 1

    # Trigger fast copier synchronization immediately upon receiving telemetry
    try:
        copier_engine.sync_copy_groups()
    except Exception as e:
        pass

    # Fast-path: immediately return any newly generated commands for this node
    commands = get_pending_node_commands(node_id)

    return {
        "success": True,
        "updated_count": count,
        "commands": commands
    }

@router.get("/{node_id}/commands")
def get_node_commands(node_id: str, x_node_api_key: Optional[str] = Header(None)):
    """Fetches any pending trade execution commands assigned to this hardware node."""
    node = get_node_by_id(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Worker Node '{node_id}' not found.")
    if x_node_api_key and node["api_key"] and x_node_api_key != node["api_key"]:
        raise HTTPException(status_code=401, detail="Invalid node API key")

    commands = get_pending_node_commands(node_id)
    return {
        "success": True,
        "node_id": node_id,
        "commands": commands
    }

@router.post("/{node_id}/commands/{cmd_id}/result")
def submit_command_result(node_id: str, cmd_id: str, payload: dict, x_node_api_key: Optional[str] = Header(None)):
    """Reports execution result (ticket, price, retcode) for a trade command back to Hub."""
    node = get_node_by_id(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Worker Node '{node_id}' not found.")
    if x_node_api_key and node["api_key"] and x_node_api_key != node["api_key"]:
        raise HTTPException(status_code=401, detail="Invalid node API key")

    status = payload.get("status", "success")
    complete_node_command(cmd_id, status, payload)
    copier_engine.handle_command_result(cmd_id, payload)
    return {"success": True, "message": "Command result recorded."}

@router.get("/quick-setup")
def generate_quick_setup_info(hub_host: Optional[str] = Query(None)):
    new_token = f"node_token_{uuid.uuid4().hex[:12]}"
    suggested_id = f"node-{uuid.uuid4().hex[:6]}"
    host = hub_host or f"http://YOUR_SERVER_IP:{settings.PORT}"
    
    ps_cmd = f"""# Run this in PowerShell on your new VPS / hardware:
git clone <repo-url> mt5-worker
cd mt5-worker\\worker_node
$env:HUB_URL="{host}"
$env:NODE_ID="{suggested_id}"
$env:NODE_API_KEY="{new_token}"
.\\start_worker.ps1
"""
    return {
        "success": True,
        "hub_url": host,
        "suggested_node_id": suggested_id,
        "api_key": new_token,
        "powershell_command": ps_cmd,
        "env_snippet": f"""HUB_URL={host}
NODE_ID={suggested_id}
NODE_NAME="New Hardware Node"
NODE_API_KEY={new_token}
MASTER_MT5_DIR=C:\\MT5_Master
CLIENTS_DIR=.\\CLIENTS
MAX_TERMINALS=30
POLL_INTERVAL=10
"""
    }
