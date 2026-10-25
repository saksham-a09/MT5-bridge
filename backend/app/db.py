import sqlite3
import json
import time
import threading
from datetime import datetime, timezone
from contextlib import contextmanager
from typing import List, Dict, Any, Optional, Set
from .config import settings

db_lock = threading.RLock()

def get_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _extract_today_closed_pnl_from_deals(deals_raw: Any, today_dates: Set[str]) -> float:
    if not deals_raw:
        return 0.0
    try:
        deals = json.loads(deals_raw) if isinstance(deals_raw, str) else deals_raw
        if not isinstance(deals, list):
            return 0.0
        total = 0.0
        for d in deals:
            t_val = d.get("time", "")
            match = False
            if isinstance(t_val, str):
                match = any(t_val.startswith(td) for td in today_dates)
            elif isinstance(t_val, (int, float)):
                try:
                    d_dt = datetime.fromtimestamp(t_val, timezone.utc).strftime("%Y-%m-%d")
                    match = d_dt in today_dates
                except Exception:
                    pass
            if match:
                profit = float(d.get("profit", 0.0) or 0.0)
                swap = float(d.get("swap", 0.0) or 0.0)
                comm = float(d.get("commission", 0.0) or 0.0)
                fee = float(d.get("fee", 0.0) or 0.0)
                total += (profit + swap + comm + fee)
        return round(total, 2)
    except Exception:
        return 0.0

@contextmanager
def get_db():
    with db_lock:
        conn = sqlite3.connect(settings.DATABASE_PATH, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA temp_store = MEMORY;")
        conn.execute("PRAGMA busy_timeout = 30000;")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

def init_db():
    """Initializes tables and default data."""
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            login INTEGER PRIMARY KEY,
            password TEXT NOT NULL,
            server TEXT NOT NULL,
            name TEXT DEFAULT '',
            status TEXT DEFAULT 'active',
            assigned_node_id TEXT DEFAULT NULL,
            target_node_id TEXT DEFAULT 'auto',
            expert TEXT DEFAULT '',
            symbol TEXT DEFAULT '',
            timeframe TEXT DEFAULT '',
            created_at TEXT,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS worker_nodes (
            node_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            api_key TEXT NOT NULL,
            ip_address TEXT DEFAULT '',
            status TEXT DEFAULT 'offline',
            max_terminals INTEGER DEFAULT 25,
            active_terminals INTEGER DEFAULT 0,
            cpu_percent REAL DEFAULT 0.0,
            ram_percent REAL DEFAULT 0.0,
            ram_used_mb REAL DEFAULT 0.0,
            ram_total_mb REAL DEFAULT 0.0,
            os_info TEXT DEFAULT '',
            last_heartbeat TEXT,
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS account_telemetry (
            login INTEGER PRIMARY KEY,
            is_connected INTEGER DEFAULT 0,
            broker_name TEXT DEFAULT '',
            server TEXT DEFAULT '',
            currency TEXT DEFAULT 'USD',
            leverage INTEGER DEFAULT 100,
            balance REAL DEFAULT 0.0,
            equity REAL DEFAULT 0.0,
            profit REAL DEFAULT 0.0,
            daily_closed_pnl REAL DEFAULT 0.0,
            margin REAL DEFAULT 0.0,
            margin_free REAL DEFAULT 0.0,
            margin_level REAL DEFAULT 0.0,
            ping INTEGER DEFAULT 0,
            open_positions TEXT DEFAULT '[]',
            pending_orders TEXT DEFAULT '[]',
            deals_history TEXT DEFAULT '[]',
            error_message TEXT DEFAULT '',
            last_sync TEXT,
            FOREIGN KEY (login) REFERENCES accounts (login) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT DEFAULT 'INFO',
            source TEXT DEFAULT 'HUB',
            message TEXT NOT NULL,
            details TEXT DEFAULT '{}',
            created_at TEXT
        );

        CREATE TABLE IF NOT EXISTS copy_groups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            master_login INTEGER NOT NULL,
            status TEXT DEFAULT 'active',
            risk_type TEXT DEFAULT 'multiplier',
            multiplier REAL DEFAULT 1.0,
            fixed_lot REAL DEFAULT 0.01,
            max_slippage_points INTEGER DEFAULT 20,
            copy_sl_tp INTEGER DEFAULT 1,
            copy_pending_orders INTEGER DEFAULT 1,
            symbol_mappings TEXT DEFAULT '{}',
            created_at TEXT,
            updated_at TEXT,
            FOREIGN KEY (master_login) REFERENCES accounts (login) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS copy_group_slaves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            slave_login INTEGER NOT NULL,
            status TEXT DEFAULT 'active',
            custom_multiplier REAL DEFAULT NULL,
            custom_fixed_lot REAL DEFAULT NULL,
            created_at TEXT,
            FOREIGN KEY (group_id) REFERENCES copy_groups (id) ON DELETE CASCADE,
            FOREIGN KEY (slave_login) REFERENCES accounts (login) ON DELETE CASCADE,
            UNIQUE(group_id, slave_login)
        );

        CREATE TABLE IF NOT EXISTS copied_trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id INTEGER NOT NULL,
            master_login INTEGER NOT NULL,
            slave_login INTEGER NOT NULL,
            master_ticket INTEGER NOT NULL,
            slave_ticket INTEGER DEFAULT 0,
            symbol TEXT NOT NULL,
            order_type TEXT NOT NULL,
            master_volume REAL NOT NULL,
            slave_volume REAL NOT NULL,
            master_open_price REAL DEFAULT 0.0,
            slave_open_price REAL DEFAULT 0.0,
            status TEXT DEFAULT 'open',
            error_message TEXT DEFAULT '',
            opened_at TEXT,
            closed_at TEXT,
            master_profit REAL DEFAULT 0.0,
            slave_profit REAL DEFAULT 0.0,
            execution_ms INTEGER DEFAULT 0,
            FOREIGN KEY (group_id) REFERENCES copy_groups (id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS copy_node_commands (
            id TEXT PRIMARY KEY,
            node_id TEXT NOT NULL,
            login INTEGER NOT NULL,
            action TEXT NOT NULL,
            payload TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            result TEXT DEFAULT '{}',
            created_at TEXT,
            completed_at TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_accounts_status ON accounts(status);
        CREATE INDEX IF NOT EXISTS idx_accounts_node ON accounts(assigned_node_id);
        CREATE INDEX IF NOT EXISTS idx_logs_created ON system_logs(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_copy_groups_master ON copy_groups(master_login);
        CREATE INDEX IF NOT EXISTS idx_copy_slaves_group ON copy_group_slaves(group_id);
        CREATE INDEX IF NOT EXISTS idx_copied_trades_lookup ON copied_trades(master_ticket, slave_login);
        CREATE INDEX IF NOT EXISTS idx_node_commands_pending ON copy_node_commands(node_id, status);
        """)

        # Migration: ensure pending_orders and daily_closed_pnl columns exist
        try:
            cursor = conn.execute("PRAGMA table_info(account_telemetry)")
            existing_cols = {row[1] for row in cursor.fetchall()}
            if "pending_orders" not in existing_cols:
                conn.execute("ALTER TABLE account_telemetry ADD COLUMN pending_orders TEXT DEFAULT '[]'")
            if "daily_closed_pnl" not in existing_cols:
                conn.execute("ALTER TABLE account_telemetry ADD COLUMN daily_closed_pnl REAL DEFAULT 0.0")
        except Exception:
            pass

        # Reconcile stale open copied trades if positions are empty in telemetry
        try:
            tel_rows = conn.execute("SELECT login, open_positions, deals_history FROM account_telemetry").fetchall()
            open_pos_by_login = {}
            deals_by_login = {}
            for tr in tel_rows:
                try:
                    open_pos_by_login[tr["login"]] = {int(p.get("ticket", 0)) for p in json.loads(tr["open_positions"] or "[]")}
                except Exception:
                    open_pos_by_login[tr["login"]] = set()
                try:
                    deals_by_login[tr["login"]] = json.loads(tr["deals_history"] or "[]")
                except Exception:
                    deals_by_login[tr["login"]] = []

            if open_pos_by_login:
                open_trades = conn.execute("SELECT id, master_login, slave_login, master_ticket, slave_ticket, opened_at FROM copied_trades WHERE status = 'open'").fetchall()
                now_iso = get_iso_now()
                for ot in open_trades:
                    m_login = ot["master_login"]
                    s_login = ot["slave_login"]
                    m_ticket = ot["master_ticket"]
                    s_ticket = ot["slave_ticket"]
                    if m_login in open_pos_by_login and m_ticket not in open_pos_by_login[m_login]:
                        s_open_tickets = open_pos_by_login.get(s_login, set())
                        if s_ticket not in s_open_tickets:
                            m_profit = 0.0
                            s_profit = 0.0
                            closed_at = now_iso
                            for d in deals_by_login.get(m_login, []):
                                if d.get("ticket") == m_ticket:
                                    m_profit = float(d.get("profit", 0.0))
                                    if d.get("time"):
                                        closed_at = d["time"]
                                    break
                            for d in deals_by_login.get(s_login, []):
                                if d.get("ticket") == s_ticket or str(m_ticket) in str(d.get("comment", "")):
                                    s_profit = float(d.get("profit", 0.0))
                                    if d.get("time") and closed_at == now_iso:
                                        closed_at = d["time"]
                                    break
                            conn.execute("""
                                UPDATE copied_trades
                                SET status = 'closed', closed_at = ?, master_profit = ?, slave_profit = ?
                                WHERE id = ?
                            """, (closed_at, m_profit, s_profit, ot["id"]))
        except Exception:
            pass

# --- Logging Helpers ---
def add_log(message: str, level: str = "INFO", source: str = "HUB", details: Optional[Dict[str, Any]] = None, conn: Optional[sqlite3.Connection] = None):
    try:
        now = get_iso_now()
        payload = json.dumps(details or {})
        if conn:
            conn.execute(
                "INSERT INTO system_logs (level, source, message, details, created_at) VALUES (?, ?, ?, ?, ?)",
                (level, source, message, payload, now)
            )
        else:
            with get_db() as c:
                c.execute(
                    "INSERT INTO system_logs (level, source, message, details, created_at) VALUES (?, ?, ?, ?, ?)",
                    (level, source, message, payload, now)
                )
    except Exception as e:
        print(f"Failed to write log: {e}")

def get_logs(limit: int = 50) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM system_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["details"] = json.loads(d["details"])
            except Exception:
                pass
            result.append(d)
        return result

# --- Accounts Helpers ---
def get_all_accounts(status_filter: Optional[str] = None, search: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_db() as conn:
        query = """
        SELECT a.*, 
               t.is_connected, t.broker_name, t.currency, t.leverage, 
               t.balance, t.equity, t.profit, t.daily_closed_pnl, t.margin, t.margin_free, t.margin_level,
               t.ping, t.open_positions, t.pending_orders, t.deals_history, t.error_message, t.last_sync,
               w.name as node_name, w.status as node_status
        FROM accounts a
        LEFT JOIN account_telemetry t ON a.login = t.login
        LEFT JOIN worker_nodes w ON a.assigned_node_id = w.node_id
        WHERE 1=1
        """
        params = []
        if status_filter and status_filter.lower() != "all":
            query += " AND a.status = ?"
            params.append(status_filter)
        if search:
            query += " AND (CAST(a.login AS TEXT) LIKE ? OR a.server LIKE ? OR a.name LIKE ?)"
            term = f"%{search}%"
            params.extend([term, term, term])
            
        query += " ORDER BY a.created_at DESC"
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        accounts = []
        today_dates = {datetime.now(timezone.utc).strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m-%d")}
        for r in rows:
            acc = dict(r)
            try:
                acc["open_positions"] = json.loads(acc.get("open_positions") or "[]")
            except Exception:
                acc["open_positions"] = []
            try:
                acc["pending_orders"] = json.loads(acc.get("pending_orders") or "[]")
            except Exception:
                acc["pending_orders"] = []
            try:
                acc["deals_history"] = json.loads(acc.get("deals_history") or "[]")
            except Exception:
                acc["deals_history"] = []
            acc["open_positions_count"] = len(acc["open_positions"])
            acc["pending_orders_count"] = len(acc["pending_orders"])
            if (not acc.get("daily_closed_pnl") or float(acc.get("daily_closed_pnl") or 0.0) == 0.0) and acc.get("deals_history"):
                acc["daily_closed_pnl"] = _extract_today_closed_pnl_from_deals(acc["deals_history"], today_dates)
            accounts.append(acc)
        return accounts

def get_account_by_login(login: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    def _fetch(c):
        cursor = c.execute("""
        SELECT a.*, 
               t.is_connected, t.broker_name, t.currency, t.leverage, 
               t.balance, t.equity, t.profit, t.daily_closed_pnl, t.margin, t.margin_free, t.margin_level,
               t.ping, t.open_positions, t.pending_orders, t.deals_history, t.error_message, t.last_sync,
               w.name as node_name, w.status as node_status
        FROM accounts a
        LEFT JOIN account_telemetry t ON a.login = t.login
        LEFT JOIN worker_nodes w ON a.assigned_node_id = w.node_id
        WHERE a.login = ?
        """, (login,))
        row = cursor.fetchone()
        if not row:
            return None
        acc = dict(row)
        try:
            acc["open_positions"] = json.loads(acc.get("open_positions") or "[]")
        except Exception:
            acc["open_positions"] = []
        try:
            acc["pending_orders"] = json.loads(acc.get("pending_orders") or "[]")
        except Exception:
            acc["pending_orders"] = []
        try:
            acc["deals_history"] = json.loads(acc.get("deals_history") or "[]")
        except Exception:
            acc["deals_history"] = []
        acc["open_positions_count"] = len(acc["open_positions"])
        acc["pending_orders_count"] = len(acc["pending_orders"])
        if (not acc.get("daily_closed_pnl") or float(acc.get("daily_closed_pnl") or 0.0) == 0.0) and acc.get("deals_history"):
            today_dates = {datetime.now(timezone.utc).strftime("%Y-%m-%d"), datetime.now().strftime("%Y-%m-%d")}
            acc["daily_closed_pnl"] = _extract_today_closed_pnl_from_deals(acc["deals_history"], today_dates)
        return acc

    if conn:
        return _fetch(conn)
    with get_db() as c:
        return _fetch(c)

def create_account(login: int, password: str, server: str, name: str = "", target_node_id: str = "auto",
                   expert: str = "", symbol: str = "", timeframe: str = "") -> Dict[str, Any]:
    now = get_iso_now()
    with get_db() as conn:
        conn.execute("""
        INSERT INTO accounts (login, password, server, name, status, assigned_node_id, target_node_id,
                             expert, symbol, timeframe, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'active', NULL, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(login) DO UPDATE SET
            password=excluded.password,
            server=excluded.server,
            name=excluded.name,
            status='active',
            target_node_id=excluded.target_node_id,
            expert=excluded.expert,
            symbol=excluded.symbol,
            timeframe=excluded.timeframe,
            updated_at=excluded.updated_at
        """, (login, password, server, name, target_node_id, expert, symbol, timeframe, now, now))

        # Ensure telemetry row exists
        conn.execute("""
        INSERT OR IGNORE INTO account_telemetry (login, is_connected, server, last_sync)
        VALUES (?, 0, ?, ?)
        """, (login, server, now))
        add_log(f"Account {login} ({server}) added/updated in database.", source="DB", conn=conn)

    return get_account_by_login(login)

def create_accounts_bulk(accounts_data: List[Dict[str, Any]], overwrite_existing: bool = True) -> Dict[str, Any]:
    now = get_iso_now()
    results: Dict[str, Any] = {
        "total": len(accounts_data),
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": [],
        "accounts": []
    }
    
    with get_db() as conn:
        for idx, item in enumerate(accounts_data):
            try:
                login_raw = item.get("login")
                if login_raw is None or str(login_raw).strip() == "":
                    results["errors"].append({"index": idx, "login": None, "error": "Missing login ID"})
                    continue
                try:
                    login = int(login_raw)
                except (ValueError, TypeError):
                    results["errors"].append({"index": idx, "login": login_raw, "error": "Login ID must be a numeric integer"})
                    continue

                password = str(item.get("password") or "").strip()
                server = str(item.get("server") or "").strip()
                name = str(item.get("name") or "").strip() or f"Account {login}"
                target_node_id = str(item.get("target_node_id") or "auto").strip() or "auto"
                expert = str(item.get("expert") or "").strip()
                symbol = str(item.get("symbol") or "XAUUSD").strip() or "XAUUSD"
                timeframe = str(item.get("timeframe") or "M1").strip() or "M1"

                if not password:
                    results["errors"].append({"index": idx, "login": login, "error": "Password cannot be empty"})
                    continue
                if not server:
                    results["errors"].append({"index": idx, "login": login, "error": "Broker server name cannot be empty"})
                    continue

                existing = conn.execute("SELECT login FROM accounts WHERE login = ?", (login,)).fetchone()
                if existing:
                    if not overwrite_existing:
                        results["skipped"] += 1
                        continue

                    conn.execute("""
                        UPDATE accounts SET
                            password = ?,
                            server = ?,
                            name = ?,
                            status = 'active',
                            target_node_id = ?,
                            expert = ?,
                            symbol = ?,
                            timeframe = ?,
                            updated_at = ?
                        WHERE login = ?
                    """, (password, server, name, target_node_id, expert, symbol, timeframe, now, login))
                    results["updated"] += 1
                else:
                    conn.execute("""
                        INSERT INTO accounts (login, password, server, name, status, assigned_node_id, target_node_id,
                                             expert, symbol, timeframe, created_at, updated_at)
                        VALUES (?, ?, ?, ?, 'active', NULL, ?, ?, ?, ?, ?, ?)
                    """, (login, password, server, name, target_node_id, expert, symbol, timeframe, now, now))

                    conn.execute("""
                        INSERT OR IGNORE INTO account_telemetry (login, is_connected, server, last_sync)
                        VALUES (?, 0, ?, ?)
                    """, (login, server, now))
                    results["created"] += 1

            except Exception as e:
                results["errors"].append({"index": idx, "login": item.get("login"), "error": str(e)})

        total_processed = results["created"] + results["updated"]
        if total_processed > 0:
            add_log(
                f"Bulk account import processed {total_processed} accounts: {results['created']} added, {results['updated']} updated, {results['skipped']} skipped, {len(results['errors'])} errors.",
                source="DB",
                conn=conn
            )

    # Fetch accounts that were successfully processed
    for item in accounts_data:
        try:
            l = int(item.get("login", 0))
            if l:
                acc = get_account_by_login(l)
                if acc and acc not in results["accounts"]:
                    results["accounts"].append(acc)
        except Exception:
            pass

    return results

def update_account(login: int, **fields) -> Optional[Dict[str, Any]]:
    if not fields:
        return get_account_by_login(login)
    fields["updated_at"] = get_iso_now()
    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values()) + [login]
    with get_db() as conn:
        conn.execute(f"UPDATE accounts SET {set_clause} WHERE login = ?", values)
    return get_account_by_login(login)

def delete_account(login: int) -> bool:
    with get_db() as conn:
        conn.execute("DELETE FROM accounts WHERE login = ?", (login,))
        conn.execute("DELETE FROM account_telemetry WHERE login = ?", (login,))
        add_log(f"Account {login} removed from database.", source="DB", conn=conn)
    return True

def set_account_status(login: int, status: str) -> Optional[Dict[str, Any]]:
    now = get_iso_now()
    with get_db() as conn:
        conn.execute("UPDATE accounts SET status = ?, updated_at = ? WHERE login = ?", (status, now, login))
        if status == "stopped":
            conn.execute("UPDATE account_telemetry SET is_connected = 0 WHERE login = ?", (login,))
        add_log(f"Account {login} status changed to {status}.", source="DB", conn=conn)
    return get_account_by_login(login)

def batch_account_action(logins: List[int], action: str, target_node_id: Optional[str] = None) -> Dict[str, Any]:
    if not logins:
        return {"success": True, "action": action, "affected": 0, "logins": []}

    now = get_iso_now()
    clean_logins = [int(l) for l in logins]
    placeholders = ",".join(["?"] * len(clean_logins))

    with get_db() as conn:
        if action == "start":
            conn.execute(f"UPDATE accounts SET status = 'active', updated_at = ? WHERE login IN ({placeholders})", [now] + clean_logins)
            add_log(f"Batch action: activated {len(clean_logins)} accounts.", source="DB", conn=conn)

        elif action == "stop":
            conn.execute(f"UPDATE accounts SET status = 'stopped', updated_at = ? WHERE login IN ({placeholders})", [now] + clean_logins)
            conn.execute(f"UPDATE account_telemetry SET is_connected = 0 WHERE login IN ({placeholders})", clean_logins)
            add_log(f"Batch action: stopped {len(clean_logins)} accounts.", source="DB", conn=conn)

        elif action == "restart":
            conn.execute(f"UPDATE accounts SET status = 'stopped', updated_at = ? WHERE login IN ({placeholders})", [now] + clean_logins)
            conn.execute(f"UPDATE accounts SET status = 'active', updated_at = ? WHERE login IN ({placeholders})", [now] + clean_logins)
            add_log(f"Batch action: restart signal sent for {len(clean_logins)} accounts.", source="DB", conn=conn)

        elif action == "delete":
            conn.execute(f"DELETE FROM accounts WHERE login IN ({placeholders})", clean_logins)
            conn.execute(f"DELETE FROM account_telemetry WHERE login IN ({placeholders})", clean_logins)
            add_log(f"Batch action: deleted {len(clean_logins)} accounts from database.", source="DB", conn=conn)

        elif action == "assign_node":
            node_val = str(target_node_id or "auto")
            conn.execute(f"UPDATE accounts SET target_node_id = ?, updated_at = ? WHERE login IN ({placeholders})", [node_val, now] + clean_logins)
            add_log(f"Batch action: assigned {len(clean_logins)} accounts to node '{node_val}'.", source="DB", conn=conn)

        elif action == "close_all_positions":
            cursor = conn.execute(f"SELECT login, assigned_node_id FROM accounts WHERE login IN ({placeholders}) AND status = 'active'", clean_logins)
            rows = cursor.fetchall()
            for r in rows:
                l_id = r["login"]
                n_id = r["assigned_node_id"]
                if n_id:
                    enqueue_node_command(n_id, l_id, "CLOSE_ALL", {"action": "CLOSE_ALL"})
            add_log(f"Batch action: close all positions signal sent for {len(rows)} active accounts.", source="DB", conn=conn)

        elif action == "cancel_all_orders":
            cursor = conn.execute(f"SELECT login, assigned_node_id FROM accounts WHERE login IN ({placeholders}) AND status = 'active'", clean_logins)
            rows = cursor.fetchall()
            for r in rows:
                l_id = r["login"]
                n_id = r["assigned_node_id"]
                if n_id:
                    enqueue_node_command(n_id, l_id, "CANCEL_ALL_PENDING", {"action": "CANCEL_ALL_PENDING"})
            add_log(f"Batch action: cancel all pending orders signal sent for {len(rows)} active accounts.", source="DB", conn=conn)

    return {"success": True, "action": action, "affected": len(clean_logins), "logins": clean_logins}

# --- Worker Nodes Helpers ---
def get_all_nodes() -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM worker_nodes ORDER BY created_at ASC")
        return [dict(r) for r in cursor.fetchall()]

def get_node_by_id(node_id: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    if conn:
        cursor = conn.execute("SELECT * FROM worker_nodes WHERE node_id = ?", (node_id,))
        row = cursor.fetchone()
        return dict(row) if row else None
    with get_db() as c:
        cursor = c.execute("SELECT * FROM worker_nodes WHERE node_id = ?", (node_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def register_node(node_id: str, name: str, api_key: str, ip_address: str = "", max_terminals: int = 25,
                  os_info: str = "") -> Dict[str, Any]:
    now = get_iso_now()
    with get_db() as conn:
        conn.execute("""
        INSERT INTO worker_nodes (node_id, name, api_key, ip_address, status, max_terminals,
                                  active_terminals, cpu_percent, ram_percent, os_info, last_heartbeat, created_at)
        VALUES (?, ?, ?, ?, 'online', ?, 0, 0.0, 0.0, ?, ?, ?)
        ON CONFLICT(node_id) DO UPDATE SET
            name=excluded.name,
            api_key=excluded.api_key,
            ip_address=excluded.ip_address,
            status='online',
            max_terminals=excluded.max_terminals,
            os_info=excluded.os_info,
            last_heartbeat=excluded.last_heartbeat
        """, (node_id, name, api_key, ip_address, max_terminals, os_info, now, now))
        add_log(f"Worker Node '{name}' ({node_id}) registered successfully.", source="NODE", conn=conn)
        return get_node_by_id(node_id, conn=conn)

def update_node_heartbeat(node_id: str, cpu_percent: float, ram_percent: float, ram_used_mb: float,
                          ram_total_mb: float, active_terminals: int, ip_address: str = "") -> bool:
    now = get_iso_now()
    with get_db() as conn:
        params = [cpu_percent, ram_percent, ram_used_mb, ram_total_mb, active_terminals, now]
        query = """
        UPDATE worker_nodes 
        SET status = 'online', cpu_percent = ?, ram_percent = ?, ram_used_mb = ?,
            ram_total_mb = ?, active_terminals = ?, last_heartbeat = ?
        """
        if ip_address:
            query += ", ip_address = ?"
            params.append(ip_address)
        query += " WHERE node_id = ?"
        params.append(node_id)
        cursor = conn.execute(query, params)
        return cursor.rowcount > 0

def delete_node(node_id: str) -> bool:
    with get_db() as conn:
        # Unassign accounts currently on this node
        conn.execute("UPDATE accounts SET assigned_node_id = NULL WHERE assigned_node_id = ?", (node_id,))
        conn.execute("DELETE FROM worker_nodes WHERE node_id = ?", (node_id,))
        add_log(f"Worker Node '{node_id}' removed from system.", level="WARNING", source="NODE", conn=conn)
    return True

# --- Telemetry Helpers ---
def update_account_telemetry(login: int, data: Dict[str, Any]):
    now = get_iso_now()
    with get_db() as conn:
        conn.execute("""
        INSERT INTO account_telemetry (
            login, is_connected, broker_name, server, currency, leverage,
            balance, equity, profit, daily_closed_pnl, margin, margin_free, margin_level,
            ping, open_positions, pending_orders, deals_history, error_message, last_sync
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(login) DO UPDATE SET
            is_connected = excluded.is_connected,
            broker_name = excluded.broker_name,
            server = excluded.server,
            currency = excluded.currency,
            leverage = excluded.leverage,
            balance = excluded.balance,
            equity = excluded.equity,
            profit = excluded.profit,
            daily_closed_pnl = excluded.daily_closed_pnl,
            margin = excluded.margin,
            margin_free = excluded.margin_free,
            margin_level = excluded.margin_level,
            ping = excluded.ping,
            open_positions = excluded.open_positions,
            pending_orders = excluded.pending_orders,
            deals_history = excluded.deals_history,
            error_message = excluded.error_message,
            last_sync = excluded.last_sync
        """, (
            login,
            1 if data.get("is_connected") else 0,
            data.get("broker_name", ""),
            data.get("server", ""),
            data.get("currency", "USD"),
            data.get("leverage", 100),
            float(data.get("balance", 0.0)),
            float(data.get("equity", 0.0)),
            float(data.get("profit", 0.0)),
            float(data.get("daily_closed_pnl", 0.0)),
            float(data.get("margin", 0.0)),
            float(data.get("margin_free", 0.0)),
            float(data.get("margin_level", 0.0)),
            int(data.get("ping", 0)),
            json.dumps(data.get("open_positions", [])),
            json.dumps(data.get("pending_orders", [])),
            json.dumps(data.get("deals_history", [])),
            data.get("error_message", ""),
            now
        ))

def update_accounts_telemetry_batch(telemetries: List[Any]):
    """Atomic batch update of telemetry for multiple accounts in a single database transaction."""
    if not telemetries:
        return
    now = get_iso_now()
    batch_params = []
    for item in telemetries:
        data = item.model_dump() if hasattr(item, "model_dump") else (item.dict() if hasattr(item, "dict") else item)
        login = data.get("login")
        if not login:
            continue
        batch_params.append((
            int(login),
            1 if data.get("is_connected") else 0,
            data.get("broker_name", ""),
            data.get("server", ""),
            data.get("currency", "USD"),
            data.get("leverage", 100),
            float(data.get("balance", 0.0)),
            float(data.get("equity", 0.0)),
            float(data.get("profit", 0.0)),
            float(data.get("daily_closed_pnl", 0.0)),
            float(data.get("margin", 0.0)),
            float(data.get("margin_free", 0.0)),
            float(data.get("margin_level", 0.0)),
            int(data.get("ping", 0)),
            json.dumps(data.get("open_positions", [])),
            json.dumps(data.get("pending_orders", [])),
            json.dumps(data.get("deals_history", [])),
            data.get("error_message", ""),
            now
        ))

    if not batch_params:
        return

    with get_db() as conn:
        conn.executemany("""
        INSERT INTO account_telemetry (
            login, is_connected, broker_name, server, currency, leverage,
            balance, equity, profit, daily_closed_pnl, margin, margin_free, margin_level,
            ping, open_positions, pending_orders, deals_history, error_message, last_sync
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(login) DO UPDATE SET
            is_connected = excluded.is_connected,
            broker_name = excluded.broker_name,
            server = excluded.server,
            currency = excluded.currency,
            leverage = excluded.leverage,
            balance = excluded.balance,
            equity = excluded.equity,
            profit = excluded.profit,
            daily_closed_pnl = excluded.daily_closed_pnl,
            margin = excluded.margin,
            margin_free = excluded.margin_free,
            margin_level = excluded.margin_level,
            ping = excluded.ping,
            open_positions = excluded.open_positions,
            pending_orders = excluded.pending_orders,
            deals_history = excluded.deals_history,
            error_message = excluded.error_message,
            last_sync = excluded.last_sync
        """, batch_params)

def get_assigned_accounts_for_node(node_id: str) -> List[Dict[str, Any]]:
    """Returns all accounts assigned to run on this node with their credentials and master/slave role."""
    with get_db() as conn:
        cursor = conn.execute("""
        SELECT a.login, a.password, a.server, a.name, a.status, a.expert, a.symbol, a.timeframe,
               CASE WHEN cg.id IS NOT NULL THEN 1 ELSE 0 END as is_master
        FROM accounts a
        LEFT JOIN copy_groups cg ON cg.master_login = a.login AND cg.status = 'active'
        WHERE a.assigned_node_id = ?
        """, (node_id,))
        return [dict(r) for r in cursor.fetchall()]

def get_dashboard_summary() -> Dict[str, Any]:
    with get_db() as conn:
        # Accounts summary
        acc_cursor = conn.execute("""
        SELECT 
            COUNT(*) as total_accounts,
            SUM(CASE WHEN a.status = 'active' THEN 1 ELSE 0 END) as active_accounts,
            SUM(CASE WHEN t.is_connected = 1 THEN 1 ELSE 0 END) as connected_accounts,
            SUM(COALESCE(t.balance, 0.0)) as total_balance,
            SUM(COALESCE(t.equity, 0.0)) as total_equity,
            SUM(COALESCE(t.profit, 0.0)) as total_profit
        FROM accounts a
        LEFT JOIN account_telemetry t ON a.login = t.login
        """)
        acc_stats = dict(acc_cursor.fetchone())

        # Count total open positions across all connected accounts
        pos_cursor = conn.execute("SELECT open_positions FROM account_telemetry WHERE is_connected = 1")
        total_open_positions = 0
        for row in pos_cursor.fetchall():
            try:
                positions = json.loads(row["open_positions"] or "[]")
                total_open_positions += len(positions)
            except Exception:
                pass
        acc_stats["total_open_positions"] = total_open_positions

        # Nodes summary
        node_cursor = conn.execute("""
        SELECT 
            COUNT(*) as total_nodes,
            SUM(CASE WHEN status = 'online' THEN 1 ELSE 0 END) as online_nodes,
            SUM(max_terminals) as total_terminal_capacity,
            SUM(active_terminals) as total_active_terminals,
            AVG(CASE WHEN status = 'online' THEN cpu_percent ELSE NULL END) as avg_cpu_percent,
            AVG(CASE WHEN status = 'online' THEN ram_percent ELSE NULL END) as avg_ram_percent
        FROM worker_nodes
        """)
        node_stats = dict(node_cursor.fetchone())

        # Closed PnL for the day: Master total and Slaves sum
        now_dt = datetime.now(timezone.utc)
        today_utc = now_dt.strftime("%Y-%m-%d")
        today_local = datetime.now().strftime("%Y-%m-%d")
        today_dates = {today_utc, today_local}

        # 1. Master Daily Closed PnL
        master_cur = conn.execute("""
            SELECT COALESCE(SUM(t.daily_closed_pnl), 0.0) as telemetry_pnl
            FROM account_telemetry t
            WHERE t.login IN (SELECT DISTINCT master_login FROM copy_groups)
        """)
        m_row = master_cur.fetchone()
        master_telemetry_pnl = round(float(m_row["telemetry_pnl"] if m_row else 0.0), 2)

        m_deals_pnl = 0.0
        m_deals_cur = conn.execute("""
            SELECT t.deals_history FROM account_telemetry t
            WHERE t.login IN (SELECT DISTINCT master_login FROM copy_groups)
        """)
        for row in m_deals_cur.fetchall():
            m_deals_pnl += _extract_today_closed_pnl_from_deals(row["deals_history"], today_dates)
        m_deals_pnl = round(m_deals_pnl, 2)

        m_trades_cur = conn.execute("""
            SELECT COALESCE(SUM(master_profit), 0.0) as trades_pnl
            FROM copied_trades
            WHERE status = 'closed' AND (
                closed_at LIKE ? OR closed_at LIKE ?
                OR date(closed_at) = date('now')
                OR date(closed_at, 'localtime') = date('now', 'localtime')
            )
        """, (f"{today_utc}%", f"{today_local}%"))
        m_t_row = m_trades_cur.fetchone()
        m_trades_pnl = round(float(m_t_row["trades_pnl"] if m_t_row else 0.0), 2)

        master_daily_closed_pnl = master_telemetry_pnl if master_telemetry_pnl != 0.0 else (m_deals_pnl if m_deals_pnl != 0.0 else m_trades_pnl)

        # 2. Slaves Daily Closed PnL (Total Sum across all slaves)
        slave_cur = conn.execute("""
            SELECT COALESCE(SUM(t.daily_closed_pnl), 0.0) as telemetry_pnl
            FROM account_telemetry t
            WHERE t.login IN (SELECT DISTINCT slave_login FROM copy_group_slaves)
        """)
        s_row = slave_cur.fetchone()
        slave_telemetry_pnl = round(float(s_row["telemetry_pnl"] if s_row else 0.0), 2)

        s_deals_pnl = 0.0
        s_deals_cur = conn.execute("""
            SELECT t.deals_history FROM account_telemetry t
            WHERE t.login IN (SELECT DISTINCT slave_login FROM copy_group_slaves)
        """)
        for row in s_deals_cur.fetchall():
            s_deals_pnl += _extract_today_closed_pnl_from_deals(row["deals_history"], today_dates)
        s_deals_pnl = round(s_deals_pnl, 2)

        s_trades_cur = conn.execute("""
            SELECT COALESCE(SUM(slave_profit), 0.0) as trades_pnl
            FROM copied_trades
            WHERE status = 'closed' AND (
                closed_at LIKE ? OR closed_at LIKE ?
                OR date(closed_at) = date('now')
                OR date(closed_at, 'localtime') = date('now', 'localtime')
            )
        """, (f"{today_utc}%", f"{today_local}%"))
        s_t_row = s_trades_cur.fetchone()
        s_trades_pnl = round(float(s_t_row["trades_pnl"] if s_t_row else 0.0), 2)

        slaves_daily_closed_pnl = slave_telemetry_pnl if slave_telemetry_pnl != 0.0 else (s_deals_pnl if s_deals_pnl != 0.0 else s_trades_pnl)

        acc_stats["master_daily_closed_pnl"] = master_daily_closed_pnl
        acc_stats["slaves_daily_closed_pnl"] = slaves_daily_closed_pnl

        return {
            "accounts": acc_stats,
            "nodes": node_stats,
            "master_daily_closed_pnl": master_daily_closed_pnl,
            "slaves_daily_closed_pnl": slaves_daily_closed_pnl,
            "timestamp": get_iso_now()
        }

# --- Copy Trading Helpers ---
def get_all_copy_groups() -> List[Dict[str, Any]]:
    now_dt = datetime.now(timezone.utc)
    today_utc = now_dt.strftime("%Y-%m-%d")
    today_local = datetime.now().strftime("%Y-%m-%d")
    today_dates = {today_utc, today_local}

    with get_db() as conn:
        cursor = conn.execute("""
        SELECT g.*, 
               m.name as master_name, m.server as master_server,
               (SELECT COUNT(*) FROM copy_group_slaves WHERE group_id = g.id) as slave_count,
               (SELECT COUNT(*) FROM copied_trades WHERE group_id = g.id AND status = 'open') as open_copied_trades_count,
               (SELECT COALESCE(SUM(slave_profit), 0.0) FROM copied_trades WHERE group_id = g.id) as total_slave_profit
        FROM copy_groups g
        LEFT JOIN accounts m ON g.master_login = m.login
        ORDER BY g.created_at DESC
        """)
        groups = []
        for r in cursor.fetchall():
            grp = dict(r)
            try:
                grp["symbol_mappings"] = json.loads(grp.get("symbol_mappings") or "{}")
            except Exception:
                grp["symbol_mappings"] = {}

            # Group specific closed PnL for today
            grp_m = conn.execute("""
                SELECT COALESCE(t.daily_closed_pnl, 0.0) as pnl, t.deals_history
                FROM account_telemetry t WHERE t.login = ?
            """, (grp["master_login"],)).fetchone()
            grp_m_pnl = float(grp_m["pnl"] if grp_m else 0.0)
            if grp_m_pnl == 0.0 and grp_m:
                grp_m_pnl = _extract_today_closed_pnl_from_deals(grp_m["deals_history"], today_dates)
            if grp_m_pnl == 0.0:
                grp_m_tr = conn.execute("""
                    SELECT COALESCE(SUM(master_profit), 0.0) as pnl
                    FROM copied_trades
                    WHERE group_id = ? AND status = 'closed' AND (
                        closed_at LIKE ? OR closed_at LIKE ?
                        OR date(closed_at) = date('now')
                        OR date(closed_at, 'localtime') = date('now', 'localtime')
                    )
                """, (grp["id"], f"{today_utc}%", f"{today_local}%")).fetchone()
                grp_m_pnl = float(grp_m_tr["pnl"] if grp_m_tr else 0.0)
            grp["master_daily_closed_pnl"] = round(grp_m_pnl, 2)

            grp_s = conn.execute("""
                SELECT COALESCE(SUM(t.daily_closed_pnl), 0.0) as pnl
                FROM account_telemetry t
                WHERE t.login IN (SELECT slave_login FROM copy_group_slaves WHERE group_id = ?)
            """, (grp["id"],)).fetchone()
            grp_s_telemetry = round(float(grp_s["pnl"] if grp_s else 0.0), 2)

            grp_s_deals_pnl = 0.0
            if grp_s_telemetry == 0.0:
                s_deals_rows = conn.execute("""
                    SELECT t.deals_history FROM account_telemetry t
                    WHERE t.login IN (SELECT slave_login FROM copy_group_slaves WHERE group_id = ?)
                """, (grp["id"],)).fetchall()
                for sdr in s_deals_rows:
                    grp_s_deals_pnl += _extract_today_closed_pnl_from_deals(sdr["deals_history"], today_dates)
                grp_s_deals_pnl = round(grp_s_deals_pnl, 2)

            grp_s_trades = conn.execute("""
                SELECT COALESCE(SUM(slave_profit), 0.0) as pnl
                FROM copied_trades
                WHERE group_id = ? AND status = 'closed' AND (
                    closed_at LIKE ? OR closed_at LIKE ?
                    OR date(closed_at) = date('now')
                    OR date(closed_at, 'localtime') = date('now', 'localtime')
                )
            """, (grp["id"], f"{today_utc}%", f"{today_local}%")).fetchone()
            grp_s_trades_pnl = round(float(grp_s_trades["pnl"] if grp_s_trades else 0.0), 2)

            grp["slaves_daily_closed_pnl"] = grp_s_telemetry if grp_s_telemetry != 0.0 else (grp_s_deals_pnl if grp_s_deals_pnl != 0.0 else grp_s_trades_pnl)

            slaves_cursor = conn.execute("""
            SELECT s.*, a.name as slave_name, a.server as slave_server, a.status as account_status,
                   t.is_connected, t.balance, t.equity, t.daily_closed_pnl, t.deals_history
            FROM copy_group_slaves s
            JOIN accounts a ON s.slave_login = a.login
            LEFT JOIN account_telemetry t ON s.slave_login = t.login
            WHERE s.group_id = ?
            """, (grp["id"],))
            slaves_list = []
            for s in slaves_cursor.fetchall():
                sd = dict(s)
                if (not sd.get("daily_closed_pnl") or float(sd.get("daily_closed_pnl") or 0.0) == 0.0) and sd.get("deals_history"):
                    sd["daily_closed_pnl"] = _extract_today_closed_pnl_from_deals(sd["deals_history"], today_dates)
                slaves_list.append(sd)
            grp["slaves"] = slaves_list
            groups.append(grp)
        return groups

def get_copy_group_by_id(group_id: int) -> Optional[Dict[str, Any]]:
    now_dt = datetime.now(timezone.utc)
    today_utc = now_dt.strftime("%Y-%m-%d")
    today_local = datetime.now().strftime("%Y-%m-%d")
    today_dates = {today_utc, today_local}

    with get_db() as conn:
        cursor = conn.execute("""
        SELECT g.*, 
               m.name as master_name, m.server as master_server,
               (SELECT COUNT(*) FROM copy_group_slaves WHERE group_id = g.id) as slave_count,
               (SELECT COUNT(*) FROM copied_trades WHERE group_id = g.id AND status = 'open') as open_copied_trades_count,
               (SELECT COALESCE(SUM(slave_profit), 0.0) FROM copied_trades WHERE group_id = g.id) as total_slave_profit
        FROM copy_groups g
        LEFT JOIN accounts m ON g.master_login = m.login
        WHERE g.id = ?
        """, (group_id,))
        row = cursor.fetchone()
        if not row:
            return None
        grp = dict(row)
        try:
            grp["symbol_mappings"] = json.loads(grp.get("symbol_mappings") or "{}")
        except Exception:
            grp["symbol_mappings"] = {}

        grp_m = conn.execute("""
            SELECT COALESCE(t.daily_closed_pnl, 0.0) as pnl, t.deals_history
            FROM account_telemetry t WHERE t.login = ?
        """, (grp["master_login"],)).fetchone()
        grp_m_pnl = float(grp_m["pnl"] if grp_m else 0.0)
        if grp_m_pnl == 0.0 and grp_m:
            grp_m_pnl = _extract_today_closed_pnl_from_deals(grp_m["deals_history"], today_dates)
        if grp_m_pnl == 0.0:
            grp_m_tr = conn.execute("""
                SELECT COALESCE(SUM(master_profit), 0.0) as pnl
                FROM copied_trades
                WHERE group_id = ? AND status = 'closed' AND (
                    closed_at LIKE ? OR closed_at LIKE ?
                    OR date(closed_at) = date('now')
                    OR date(closed_at, 'localtime') = date('now', 'localtime')
                )
            """, (grp["id"], f"{today_utc}%", f"{today_local}%")).fetchone()
            grp_m_pnl = float(grp_m_tr["pnl"] if grp_m_tr else 0.0)
        grp["master_daily_closed_pnl"] = round(grp_m_pnl, 2)

        grp_s = conn.execute("""
            SELECT COALESCE(SUM(t.daily_closed_pnl), 0.0) as pnl
            FROM account_telemetry t
            WHERE t.login IN (SELECT slave_login FROM copy_group_slaves WHERE group_id = ?)
        """, (grp["id"],)).fetchone()
        grp_s_telemetry = round(float(grp_s["pnl"] if grp_s else 0.0), 2)

        grp_s_deals_pnl = 0.0
        if grp_s_telemetry == 0.0:
            s_deals_rows = conn.execute("""
                SELECT t.deals_history FROM account_telemetry t
                WHERE t.login IN (SELECT slave_login FROM copy_group_slaves WHERE group_id = ?)
            """, (grp["id"],)).fetchall()
            for sdr in s_deals_rows:
                grp_s_deals_pnl += _extract_today_closed_pnl_from_deals(sdr["deals_history"], today_dates)
            grp_s_deals_pnl = round(grp_s_deals_pnl, 2)

        grp_s_trades = conn.execute("""
            SELECT COALESCE(SUM(slave_profit), 0.0) as pnl
            FROM copied_trades
            WHERE group_id = ? AND status = 'closed' AND (
                closed_at LIKE ? OR closed_at LIKE ?
                OR date(closed_at) = date('now')
                OR date(closed_at, 'localtime') = date('now', 'localtime')
            )
        """, (grp["id"], f"{today_utc}%", f"{today_local}%")).fetchone()
        grp_s_trades_pnl = round(float(grp_s_trades["pnl"] if grp_s_trades else 0.0), 2)

        grp["slaves_daily_closed_pnl"] = grp_s_telemetry if grp_s_telemetry != 0.0 else (grp_s_deals_pnl if grp_s_deals_pnl != 0.0 else grp_s_trades_pnl)

        slaves_cursor = conn.execute("""
        SELECT s.*, a.name as slave_name, a.server as slave_server, a.status as account_status,
               t.is_connected, t.balance, t.equity, t.daily_closed_pnl, t.deals_history
        FROM copy_group_slaves s
        JOIN accounts a ON s.slave_login = a.login
        LEFT JOIN account_telemetry t ON s.slave_login = t.login
        WHERE s.group_id = ?
        """, (group_id,))
        slaves_list = []
        for s in slaves_cursor.fetchall():
            sd = dict(s)
            if (not sd.get("daily_closed_pnl") or float(sd.get("daily_closed_pnl") or 0.0) == 0.0) and sd.get("deals_history"):
                sd["daily_closed_pnl"] = _extract_today_closed_pnl_from_deals(sd["deals_history"], today_dates)
            slaves_list.append(sd)
        grp["slaves"] = slaves_list
        return grp

def create_copy_group(name: str, master_login: int, risk_type: str = "multiplier",
                      multiplier: float = 1.0, fixed_lot: float = 0.01, max_slippage_points: int = 20,
                      copy_sl_tp: bool = True, copy_pending_orders: bool = True,
                      symbol_mappings: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
    now = get_iso_now()
    mappings_json = json.dumps(symbol_mappings or {})
    with get_db() as conn:
        cursor = conn.execute("""
        INSERT INTO copy_groups (
            name, master_login, status, risk_type, multiplier, fixed_lot,
            max_slippage_points, copy_sl_tp, copy_pending_orders, symbol_mappings,
            created_at, updated_at
        ) VALUES (?, ?, 'active', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name, master_login, risk_type, float(multiplier), float(fixed_lot),
            int(max_slippage_points), 1 if copy_sl_tp else 0, 1 if copy_pending_orders else 0,
            mappings_json, now, now
        ))
        group_id = cursor.lastrowid
        add_log(f"Copy Trading Group '{name}' (ID: {group_id}, Master: {master_login}) created.", source="COPIER", conn=conn)
    return get_copy_group_by_id(group_id)

def update_copy_group(group_id: int, **fields) -> Optional[Dict[str, Any]]:
    if not fields:
        return get_copy_group_by_id(group_id)
    fields["updated_at"] = get_iso_now()
    if "symbol_mappings" in fields and isinstance(fields["symbol_mappings"], dict):
        fields["symbol_mappings"] = json.dumps(fields["symbol_mappings"])
    if "copy_sl_tp" in fields:
        fields["copy_sl_tp"] = 1 if fields["copy_sl_tp"] else 0
    if "copy_pending_orders" in fields:
        fields["copy_pending_orders"] = 1 if fields["copy_pending_orders"] else 0

    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    values = list(fields.values()) + [group_id]
    with get_db() as conn:
        conn.execute(f"UPDATE copy_groups SET {set_clause} WHERE id = ?", values)
        add_log(f"Copy Group #{group_id} settings updated.", source="COPIER", conn=conn)
    return get_copy_group_by_id(group_id)

def delete_copy_group(group_id: int) -> bool:
    with get_db() as conn:
        conn.execute("DELETE FROM copy_group_slaves WHERE group_id = ?", (group_id,))
        conn.execute("DELETE FROM copy_groups WHERE id = ?", (group_id,))
        add_log(f"Copy Group #{group_id} removed.", source="COPIER", conn=conn)
    return True

def add_slave_to_group(group_id: int, slave_login: int, custom_multiplier: Optional[float] = None,
                       custom_fixed_lot: Optional[float] = None) -> bool:
    now = get_iso_now()
    with get_db() as conn:
        conn.execute("""
        INSERT INTO copy_group_slaves (group_id, slave_login, status, custom_multiplier, custom_fixed_lot, created_at)
        VALUES (?, ?, 'active', ?, ?, ?)
        ON CONFLICT(group_id, slave_login) DO UPDATE SET
            status = 'active',
            custom_multiplier = excluded.custom_multiplier,
            custom_fixed_lot = excluded.custom_fixed_lot
        """, (group_id, slave_login, custom_multiplier, custom_fixed_lot, now))
        add_log(f"Account {slave_login} added as slave to Copy Group #{group_id}.", source="COPIER", conn=conn)
    return True

def remove_slave_from_group(group_id: int, slave_login: int) -> bool:
    with get_db() as conn:
        conn.execute("DELETE FROM copy_group_slaves WHERE group_id = ? AND slave_login = ?", (group_id, slave_login))
        add_log(f"Account {slave_login} removed from Copy Group #{group_id}.", source="COPIER", conn=conn)
    return True

def record_copied_trade(group_id: int, master_login: int, slave_login: int, master_ticket: int,
                        slave_ticket: int, symbol: str, order_type: str, master_volume: float,
                        slave_volume: float, master_open_price: float = 0.0, slave_open_price: float = 0.0,
                        execution_ms: int = 0, status: str = "open") -> int:
    now = get_iso_now()
    with get_db() as conn:
        cursor = conn.execute("""
        INSERT INTO copied_trades (
            group_id, master_login, slave_login, master_ticket, slave_ticket,
            symbol, order_type, master_volume, slave_volume, master_open_price,
            slave_open_price, status, opened_at, execution_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            group_id, master_login, slave_login, master_ticket, slave_ticket,
            symbol, order_type, master_volume, slave_volume, master_open_price,
            slave_open_price, status, now, execution_ms
        ))
        trade_id = cursor.lastrowid
        add_log(
            f"Copied trade ({status}): Master {master_login} #{master_ticket} -> Slave {slave_login} #{slave_ticket} ({symbol} {order_type} {slave_volume} lots in {execution_ms}ms).",
            source="COPIER",
            conn=conn
        )
        return trade_id

def update_copied_trade(master_ticket: int, slave_login: Optional[int] = None, **fields):
    if not fields:
        return
    set_clause = ", ".join([f"{k} = ?" for k in fields.keys()])
    with get_db() as conn:
        if slave_login is not None:
            values = list(fields.values()) + [master_ticket, slave_login]
            conn.execute(f"UPDATE copied_trades SET {set_clause} WHERE master_ticket = ? AND slave_login = ?", values)
        else:
            values = list(fields.values()) + [master_ticket]
            conn.execute(f"UPDATE copied_trades SET {set_clause} WHERE master_ticket = ?", values)

def get_copied_trades(group_id: Optional[int] = None, limit: int = 100) -> List[Dict[str, Any]]:
    with get_db() as conn:
        query = """
        SELECT t.*, g.name as group_name
        FROM copied_trades t
        LEFT JOIN copy_groups g ON t.group_id = g.id
        WHERE 1=1
        """
        params = []
        if group_id:
            query += " AND t.group_id = ?"
            params.append(group_id)
        query += " ORDER BY t.id DESC LIMIT ?"
        params.append(limit)
        cursor = conn.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]

def get_active_copied_trade(master_ticket: int, slave_login: int) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.execute("""
        SELECT * FROM copied_trades
        WHERE master_ticket = ? AND slave_login = ? AND status IN ('open', 'pending')
        ORDER BY id DESC LIMIT 1
        """, (master_ticket, slave_login))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_copied_trade_by_slave_ticket(slave_ticket: int, slave_login: Optional[int] = None) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        if slave_login is not None:
            cursor = conn.execute("""
            SELECT * FROM copied_trades
            WHERE slave_ticket = ? AND slave_login = ?
            ORDER BY id DESC LIMIT 1
            """, (slave_ticket, slave_login))
        else:
            cursor = conn.execute("""
            SELECT * FROM copied_trades
            WHERE slave_ticket = ?
            ORDER BY id DESC LIMIT 1
            """, (slave_ticket,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_open_copied_trades(group_id: Optional[int] = None) -> List[Dict[str, Any]]:
    with get_db() as conn:
        query = "SELECT * FROM copied_trades WHERE status IN ('open', 'pending')"
        params = []
        if group_id:
            query += " AND group_id = ?"
            params.append(group_id)
        cursor = conn.execute(query, params)
        return [dict(r) for r in cursor.fetchall()]

# Node command queue helpers
def enqueue_node_command(node_id: str, login: int, action: str, payload: Dict[str, Any]) -> str:
    import uuid
    cmd_id = f"cmd_{uuid.uuid4().hex[:12]}"
    now = get_iso_now()
    with get_db() as conn:
        conn.execute("""
        INSERT INTO copy_node_commands (id, node_id, login, action, payload, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'pending', ?)
        """, (cmd_id, node_id, login, action, json.dumps(payload), now))
    return cmd_id

def get_pending_node_commands(node_id: str) -> List[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.execute("""
        SELECT * FROM copy_node_commands
        WHERE node_id = ? AND status = 'pending'
        ORDER BY created_at ASC
        """, (node_id,))
        rows = cursor.fetchall()
        result = []
        for r in rows:
            d = dict(r)
            try:
                d["payload"] = json.loads(d["payload"])
            except Exception:
                pass
            result.append(d)
        
        # Atomically mark retrieved commands as 'dispatched' to prevent duplicate polling races
        if result:
            cmd_ids = [r["id"] for r in result]
            placeholders = ",".join("?" for _ in cmd_ids)
            conn.execute(f"UPDATE copy_node_commands SET status = 'dispatched' WHERE id IN ({placeholders})", cmd_ids)
        
        return result

def complete_node_command(cmd_id: str, status: str, result: Dict[str, Any]):
    now = get_iso_now()
    with get_db() as conn:
        conn.execute("""
        UPDATE copy_node_commands
        SET status = ?, result = ?, completed_at = ?
        WHERE id = ?
        """, (status, json.dumps(result), now, cmd_id))

def batch_complete_node_commands(results: List[Dict[str, Any]]):
    """Completes multiple commands in a single atomic database transaction."""
    if not results:
        return
    now = get_iso_now()
    params = []
    for r in results:
        cmd_id = r.get("cmd_id") or r.get("id")
        if not cmd_id:
            continue
        status = r.get("status", "success")
        data = r.get("data") if "data" in r else r
        params.append((status, json.dumps(data), now, cmd_id))

    if not params:
        return

    with get_db() as conn:
        conn.executemany("""
        UPDATE copy_node_commands
        SET status = ?, result = ?, completed_at = ?
        WHERE id = ?
        """, params)

def get_node_command_by_id(cmd_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM copy_node_commands WHERE id = ?", (cmd_id,))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["payload"] = json.loads(d["payload"])
        except Exception:
            pass
        return d

