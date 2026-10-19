from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from .schemas import AccountCreate, AccountUpdate
from .db import (
    get_all_accounts, get_account_by_login, create_account,
    update_account, delete_account, set_account_status, add_log
)

router = APIRouter(prefix="/api/accounts", tags=["Accounts"])

@router.get("")
def list_accounts(
    status: Optional[str] = Query(None, description="Filter by status (active, stopped, all)"),
    search: Optional[str] = Query(None, description="Search term for login, server, or label")
):
    return {
        "success": True,
        "accounts": get_all_accounts(status_filter=status, search=search)
    }

@router.post("")
def add_new_account(payload: AccountCreate):
    acc = create_account(
        login=payload.login,
        password=payload.password,
        server=payload.server,
        name=payload.name or f"Account {payload.login}",
        target_node_id=payload.target_node_id or "auto",
        expert=payload.expert or "",
        symbol=payload.symbol or "XAUUSD",
        timeframe=payload.timeframe or "M1"
    )
    return {
        "success": True,
        "message": f"Account {payload.login} saved and queued for execution.",
        "account": acc
    }

@router.get("/{login}")
def get_account(login: int):
    acc = get_account_by_login(login)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    return {
        "success": True,
        "account": acc
    }

@router.put("/{login}")
def edit_account(login: int, payload: AccountUpdate):
    existing = get_account_by_login(login)
    if not existing:
        raise HTTPException(status_code=404, detail="Account not found")
    
    update_dict = payload.model_dump(exclude_unset=True)
    updated = update_account(login, **update_dict)
    return {
        "success": True,
        "message": f"Account {login} updated.",
        "account": updated
    }

@router.delete("/{login}")
def remove_account(login: int):
    existing = get_account_by_login(login)
    if not existing:
        raise HTTPException(status_code=404, detail="Account not found")
    
    delete_account(login)
    return {
        "success": True,
        "message": f"Account {login} successfully deleted."
    }

@router.post("/{login}/start")
def start_account(login: int):
    acc = get_account_by_login(login)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    
    updated = set_account_status(login, "active")
    return {
        "success": True,
        "message": f"Account {login} activated.",
        "account": updated
    }

@router.post("/{login}/stop")
def stop_account(login: int):
    acc = get_account_by_login(login)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    
    updated = set_account_status(login, "stopped")
    return {
        "success": True,
        "message": f"Account {login} stopped.",
        "account": updated
    }

@router.post("/{login}/restart")
def restart_account(login: int):
    acc = get_account_by_login(login)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Toggle to trigger worker recreation
    set_account_status(login, "stopped")
    updated = set_account_status(login, "active")
    add_log(f"Account {login} restart requested by user.", source="API")
    return {
        "success": True,
        "message": f"Restart command sent for Account {login}.",
        "account": updated
    }
