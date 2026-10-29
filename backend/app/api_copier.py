from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from .schemas import CopyGroupCreate, CopyGroupUpdate, SlaveAdd
from .db import (
    get_all_copy_groups, get_copy_group_by_id, create_copy_group,
    update_copy_group, delete_copy_group, add_slave_to_group,
    remove_slave_from_group, get_copied_trades, get_account_by_login
)
from .copier_engine import copier_engine

router = APIRouter(prefix="/api/copier", tags=["Copy Trading"])

@router.get("/groups")
def list_groups():
    """List all copy trading groups with master and slave information."""
    groups = get_all_copy_groups()
    return {
        "success": True,
        "groups": groups,
        "count": len(groups)
    }

@router.post("/groups")
def create_group(payload: CopyGroupCreate):
    """Creates a new Copy Trading Group."""
    # Validate Master account exists
    master = get_account_by_login(payload.master_login)
    if not master:
        raise HTTPException(status_code=400, detail=f"Master Account {payload.master_login} does not exist.")

    grp = create_copy_group(
        name=payload.name,
        master_login=payload.master_login,
        risk_type=payload.risk_type or "multiplier",
        multiplier=payload.multiplier or 1.0,
        fixed_lot=payload.fixed_lot or 0.01,
        max_slippage_points=payload.max_slippage_points or 20,
        copy_sl_tp=payload.copy_sl_tp if payload.copy_sl_tp is not None else True,
        copy_pending_orders=payload.copy_pending_orders if payload.copy_pending_orders is not None else True,
        symbol_mappings=payload.symbol_mappings or {}
    )

    if not grp:
        raise HTTPException(status_code=500, detail="Failed to create copy group")

    # Add initial slaves if provided
    for s_login in (payload.initial_slave_logins or []):
        if s_login != payload.master_login:
            slave_acc = get_account_by_login(s_login)
            if slave_acc:
                add_slave_to_group(grp["id"], s_login)

    # Immediately trigger sync
    copier_engine.sync_copy_groups()
    return {
        "success": True,
        "message": f"Copy Group '{payload.name}' created successfully.",
        "group": get_copy_group_by_id(grp["id"])
    }

@router.get("/groups/{group_id}")
def get_group(group_id: int):
    grp = get_copy_group_by_id(group_id)
    if not grp:
        raise HTTPException(status_code=404, detail="Copy Group not found")
    return {"success": True, "group": grp}

@router.put("/groups/{group_id}")
def update_group(group_id: int, payload: CopyGroupUpdate):
    grp = get_copy_group_by_id(group_id)
    if not grp:
        raise HTTPException(status_code=404, detail="Copy Group not found")

    update_data = payload.model_dump(exclude_unset=True)
    updated = update_copy_group(group_id, **update_data)
    copier_engine.sync_copy_groups()
    return {
        "success": True,
        "message": "Copy Group updated.",
        "group": updated
    }

@router.delete("/groups/{group_id}")
def delete_group(group_id: int):
    grp = get_copy_group_by_id(group_id)
    if not grp:
        raise HTTPException(status_code=404, detail="Copy Group not found")
    delete_copy_group(group_id)
    return {"success": True, "message": f"Copy Group #{group_id} deleted."}

@router.post("/groups/{group_id}/slaves")
def add_slave(group_id: int, payload: SlaveAdd):
    grp = get_copy_group_by_id(group_id)
    if not grp:
        raise HTTPException(status_code=404, detail="Copy Group not found")

    if payload.slave_login == grp["master_login"]:
        raise HTTPException(status_code=400, detail="An account cannot be a slave to itself.")

    slave_acc = get_account_by_login(payload.slave_login)
    if not slave_acc:
        raise HTTPException(status_code=400, detail=f"Slave Account {payload.slave_login} does not exist.")

    add_slave_to_group(
        group_id,
        payload.slave_login,
        custom_multiplier=payload.custom_multiplier,
        custom_fixed_lot=payload.custom_fixed_lot
    )
    copier_engine.sync_copy_groups()
    return {
        "success": True,
        "message": f"Slave Account {payload.slave_login} added to Group #{group_id}.",
        "group": get_copy_group_by_id(group_id)
    }

@router.delete("/groups/{group_id}/slaves/{slave_login}")
def remove_slave(group_id: int, slave_login: int):
    grp = get_copy_group_by_id(group_id)
    if not grp:
        raise HTTPException(status_code=404, detail="Copy Group not found")

    remove_slave_from_group(group_id, slave_login)
    return {
        "success": True,
        "message": f"Slave Account {slave_login} removed from Group #{group_id}."
    }

@router.get("/trades")
def list_copied_trades(group_id: Optional[int] = Query(None), limit: int = Query(50)):
    """Fetch live and historic copied trades."""
    trades = get_copied_trades(group_id=group_id, limit=limit)
    return {
        "success": True,
        "trades": trades,
        "count": len(trades)
    }

@router.post("/trigger-sync")
def trigger_manual_sync():
    """Forces an immediate synchronization cycle."""
    copier_engine.sync_copy_groups()
    return {"success": True, "message": "Copy trading synchronization triggered."}
