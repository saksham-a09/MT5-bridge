import csv
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List, Dict, Any
from .schemas import AccountCreate, AccountUpdate, AccountBulkCreate, AccountBatchAction
from .db import (
    get_all_accounts, get_account_by_login, create_account, create_accounts_bulk,
    update_account, delete_account, set_account_status, batch_account_action, add_log,
    enqueue_node_command
)

router = APIRouter(prefix="/api/accounts", tags=["Accounts"])

def parse_csv_or_text_content(
    content_str: str,
    default_server: str = "",
    default_node: str = "auto",
    default_symbol: str = "",
    default_timeframe: str = ""
) -> List[Dict[str, Any]]:
    """Robust parser for CSV/TSV/delimited text containing MT5 account credentials."""
    content_str = content_str.lstrip('\ufeff').replace('\r\n', '\n').replace('\r', '\n')
    lines = [line.strip() for line in content_str.split('\n') if line.strip() and not line.strip().startswith('#')]
    if not lines:
        return []

    # Check first line for headers
    first_line = lines[0].lower()
    has_header = False
    for kw in ['login', 'account', 'server', 'password', 'broker']:
        if kw in first_line:
            has_header = True
            break

    # Sniff delimiter
    delimiter = ','
    if '\t' in lines[0]:
        delimiter = '\t'
    elif ';' in lines[0] and ',' not in lines[0]:
        delimiter = ';'
    elif '|' in lines[0]:
        delimiter = '|'
    elif ':' in lines[0] and ',' not in lines[0] and not has_header:
        delimiter = ':'

    parsed_accounts: List[Dict[str, Any]] = []

    if has_header:
        reader = csv.DictReader(lines, delimiter=delimiter)
        for row in reader:
            normalized_row = {str(k).strip().lower().replace(' ', '_').replace('-', '_'): str(v).strip() for k, v in row.items() if k is not None}
            login_val = (
                normalized_row.get('login') or normalized_row.get('account') or
                normalized_row.get('account_id') or normalized_row.get('account_number') or
                normalized_row.get('id')
            )
            if not login_val:
                continue
            digits_only = ''.join(filter(str.isdigit, str(login_val)))
            if not digits_only:
                continue
            login_int = int(digits_only)

            password_val = normalized_row.get('password') or normalized_row.get('pass') or normalized_row.get('pwd') or ''
            server_val = normalized_row.get('server') or normalized_row.get('broker') or normalized_row.get('broker_server') or default_server
            name_val = normalized_row.get('name') or normalized_row.get('label') or normalized_row.get('account_name') or f"Account {login_int}"
            node_val = normalized_row.get('target_node_id') or normalized_row.get('node') or normalized_row.get('node_id') or default_node or 'auto'
            expert_val = normalized_row.get('expert') or normalized_row.get('ea') or ''
            symbol_val = normalized_row.get('symbol') or default_symbol or ''
            timeframe_val = normalized_row.get('timeframe') or normalized_row.get('tf') or default_timeframe or ''

            parsed_accounts.append({
                "login": login_int,
                "password": password_val,
                "server": server_val,
                "name": name_val,
                "target_node_id": node_val,
                "expert": expert_val,
                "symbol": symbol_val,
                "timeframe": timeframe_val
            })
    else:
        reader = csv.reader(lines, delimiter=delimiter)
        for row in reader:
            if not row or not row[0].strip():
                continue
            cols = [c.strip() for c in row]
            digits_only = ''.join(filter(str.isdigit, str(cols[0])))
            if not digits_only:
                continue
            login_int = int(digits_only)

            password_val = cols[1] if len(cols) > 1 else ''
            server_val = cols[2] if len(cols) > 2 and cols[2] else default_server
            name_val = cols[3] if len(cols) > 3 and cols[3] else f"Account {login_int}"
            node_val = cols[4] if len(cols) > 4 and cols[4] else default_node
            symbol_val = cols[5] if len(cols) > 5 and cols[5] else default_symbol
            timeframe_val = cols[6] if len(cols) > 6 and cols[6] else default_timeframe
            expert_val = cols[7] if len(cols) > 7 else ''

            parsed_accounts.append({
                "login": login_int,
                "password": password_val,
                "server": server_val,
                "name": name_val,
                "target_node_id": node_val,
                "expert": expert_val,
                "symbol": symbol_val,
                "timeframe": timeframe_val
            })

    return parsed_accounts

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
        symbol=payload.symbol or "",
        timeframe=payload.timeframe or ""
    )
    return {
        "success": True,
        "message": f"Account {payload.login} saved and queued for execution.",
        "account": acc
    }

@router.post("/bulk")
def add_accounts_bulk(payload: AccountBulkCreate):
    accounts_data = [acc.model_dump() for acc in payload.accounts]
    res = create_accounts_bulk(accounts_data, overwrite_existing=payload.overwrite_existing)
    return {
        "success": True,
        "message": f"Bulk import complete: {res['created']} added, {res['updated']} updated, {len(res['errors'])} failed.",
        **res
    }

@router.post("/batch-action")
def perform_batch_action(payload: AccountBatchAction):
    if not payload.logins:
        raise HTTPException(status_code=400, detail="No accounts specified.")
    valid_actions = ["start", "stop", "restart", "delete", "assign_node", "close_all_positions", "cancel_all_orders"]
    if payload.action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action. Supported: {valid_actions}")

    res = batch_account_action(payload.logins, payload.action, payload.target_node_id)
    return {
        "success": True,
        "message": f"Successfully performed '{payload.action}' on {res['affected']} accounts.",
        **res
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

@router.post("/{login}/positions/{ticket}/close")
def close_account_position(login: int, ticket: int):
    acc = get_account_by_login(login)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    node_id = acc.get("assigned_node_id")
    if not node_id:
        raise HTTPException(status_code=400, detail="Account is not currently assigned to an online worker node.")
    
    positions = acc.get("open_positions", [])
    pos = next((p for p in positions if int(p.get("ticket", 0)) == int(ticket)), None)
    symbol = pos.get("symbol", "") if pos else ""
    
    cmd_id = enqueue_node_command(
        node_id=node_id,
        login=login,
        action="CLOSE",
        payload={
            "action": "CLOSE",
            "ticket": ticket,
            "slave_ticket": ticket,
            "symbol": symbol
        }
    )
    add_log(f"Manual CLOSE requested from dashboard for Account {login}, Ticket #{ticket} ({symbol}).", source="DASHBOARD")
    return {
        "success": True,
        "message": f"Close command dispatched for Position #{ticket}.",
        "cmd_id": cmd_id
    }

@router.post("/{login}/positions/close-all")
def close_all_account_positions(login: int):
    acc = get_account_by_login(login)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    node_id = acc.get("assigned_node_id")
    if not node_id:
        raise HTTPException(status_code=400, detail="Account is not currently assigned to an online worker node.")
    
    cmd_id = enqueue_node_command(
        node_id=node_id,
        login=login,
        action="CLOSE_ALL",
        payload={"action": "CLOSE_ALL"}
    )
    add_log(f"Emergency CLOSE ALL positions requested from dashboard for Account {login}.", source="DASHBOARD", level="WARNING")
    return {
        "success": True,
        "message": f"Close-all positions command dispatched for Account {login}.",
        "cmd_id": cmd_id
    }

@router.post("/{login}/orders/{ticket}/cancel")
def cancel_account_order(login: int, ticket: int):
    acc = get_account_by_login(login)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    node_id = acc.get("assigned_node_id")
    if not node_id:
        raise HTTPException(status_code=400, detail="Account is not currently assigned to an online worker node.")
    
    cmd_id = enqueue_node_command(
        node_id=node_id,
        login=login,
        action="CANCEL_PENDING",
        payload={
            "action": "CANCEL_PENDING",
            "ticket": ticket,
            "slave_ticket": ticket
        }
    )
    add_log(f"Manual CANCEL requested from dashboard for Pending Order #{ticket} (Account {login}).", source="DASHBOARD")
    return {
        "success": True,
        "message": f"Cancel command dispatched for Order #{ticket}.",
        "cmd_id": cmd_id
    }

@router.post("/{login}/orders/cancel-all")
def cancel_all_account_orders(login: int):
    acc = get_account_by_login(login)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    node_id = acc.get("assigned_node_id")
    if not node_id:
        raise HTTPException(status_code=400, detail="Account is not currently assigned to an online worker node.")
    
    cmd_id = enqueue_node_command(
        node_id=node_id,
        login=login,
        action="CANCEL_ALL_PENDING",
        payload={"action": "CANCEL_ALL_PENDING"}
    )
    add_log(f"Emergency CANCEL ALL pending orders requested from dashboard for Account {login}.", source="DASHBOARD", level="WARNING")
    return {
        "success": True,
        "message": f"Cancel-all orders command dispatched for Account {login}.",
        "cmd_id": cmd_id
    }
