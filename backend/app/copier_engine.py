import time
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from .db import (
    get_all_copy_groups, get_account_by_login, enqueue_node_command,
    record_copied_trade, update_copied_trade, get_active_copied_trade,
    get_open_copied_trades, add_log
)

logger = logging.getLogger("TradeCopierEngine")

class TradeCopierEngine:
    def __init__(self):
        # Cache of known master positions: login -> { ticket: dict }
        self.master_positions_cache: Dict[int, Dict[int, Any]] = {}
        # Cache of known master pending orders: login -> { ticket: dict }
        self.master_pending_cache: Dict[int, Dict[int, Any]] = {}
        # In-flight commands: cmd_id -> dict
        self.pending_commands: Dict[str, Any] = {}
        # Ticket mapping: (master_ticket, slave_login) -> slave_ticket
        self.ticket_mappings: Dict[tuple, int] = {}
        # Pending ticket mapping: (master_ticket, slave_login) -> slave_ticket
        self.pending_ticket_mappings: Dict[tuple, int] = {}
        # Lock/throttling tracker: (master_ticket, slave_login) -> timestamp
        self.action_timestamps: Dict[tuple, float] = {}

    def calculate_slave_volume(
        self,
        master_volume: float,
        group_cfg: Dict[str, Any],
        slave_cfg: Dict[str, Any],
        master_telemetry: Optional[Dict[str, Any]] = None,
        slave_telemetry: Optional[Dict[str, Any]] = None
    ) -> float:
        """Calculates volume with maximum precision according to group & slave sizing rules."""
        risk_type = group_cfg.get("risk_type", "multiplier")
        multiplier = float(slave_cfg.get("custom_multiplier") or group_cfg.get("multiplier", 1.0))
        fixed_lot = float(slave_cfg.get("custom_fixed_lot") or group_cfg.get("fixed_lot", 0.01))

        if risk_type == "fixed_lot":
            return max(0.01, round(fixed_lot, 2))

        if risk_type == "equity_ratio":
            m_eq = float((master_telemetry or {}).get("equity") or 0.0)
            s_eq = float((slave_telemetry or {}).get("equity") or 0.0)
            if m_eq > 0 and s_eq > 0:
                ratio = s_eq / m_eq
                vol = master_volume * ratio * multiplier
                return max(0.01, min(100.0, round(vol, 2)))

        if risk_type == "balance_ratio":
            m_bal = float((master_telemetry or {}).get("balance") or 0.0)
            s_bal = float((slave_telemetry or {}).get("balance") or 0.0)
            if m_bal > 0 and s_bal > 0:
                ratio = s_bal / m_bal
                vol = master_volume * ratio * multiplier
                return max(0.01, min(100.0, round(vol, 2)))

        # Default: direct multiplier
        vol = master_volume * multiplier
        return max(0.01, min(100.0, round(vol, 2)))

    def map_symbol(self, symbol: str, symbol_mappings: Dict[str, str]) -> str:
        return symbol_mappings.get(symbol, symbol)

    def sync_copy_groups(self):
        """High-speed synchronization loop across all active copy groups."""
        try:
            groups = get_all_copy_groups()
            for grp in groups:
                if grp.get("status") != "active":
                    continue
                self._evaluate_group(grp)
        except Exception as e:
            logger.error(f"Error in sync_copy_groups: {e}")

    def _evaluate_group(self, grp: Dict[str, Any]):
        group_id = grp["id"]
        master_login = grp["master_login"]
        slaves = grp.get("slaves", [])
        if not slaves:
            return

        master_acc = get_account_by_login(master_login)
        if not master_acc:
            return

        master_positions = master_acc.get("open_positions", [])
        curr_master_pos_map = {int(p["ticket"]): p for p in master_positions if "ticket" in p}

        # Check previous master positions for closes
        prev_master_pos_map = self.master_positions_cache.get(master_login, {})
        self.master_positions_cache[master_login] = curr_master_pos_map

        # 1. Process Master CLOSED positions -> Close on active slaves
        for old_ticket, old_pos in prev_master_pos_map.items():
            if old_ticket not in curr_master_pos_map:
                # Master position closed!
                for s in slaves:
                    if s.get("status") != "active":
                        continue
                    slave_login = s["slave_login"]
                    self._dispatch_close(group_id, master_login, slave_login, old_ticket, old_pos)

        # 1B. Reconcile any open trades in DB whose master position is closed
        open_db_trades = get_open_copied_trades(group_id)
        for tr in open_db_trades:
            m_ticket = tr["master_ticket"]
            s_login = tr["slave_login"]
            if m_ticket not in curr_master_pos_map:
                slave_acc = get_account_by_login(s_login)
                s_positions = slave_acc.get("open_positions", []) if slave_acc else []
                s_ticket = tr.get("slave_ticket")
                slave_has_it = any(int(p.get("ticket", 0)) == s_ticket for p in s_positions) if s_ticket else False
                if slave_has_it:
                    self._dispatch_close(group_id, master_login, s_login, m_ticket, tr)
                else:
                    now_iso = datetime.now(timezone.utc).isoformat()
                    s_profit = tr.get("slave_profit", 0.0)
                    m_profit = tr.get("master_profit", 0.0)
                    if slave_acc:
                        for d in slave_acc.get("deals_history", []):
                            if d.get("ticket") == s_ticket or str(m_ticket) in str(d.get("comment", "")):
                                s_profit = float(d.get("profit", 0.0))
                                break
                    if master_acc:
                        for d in master_acc.get("deals_history", []):
                            if d.get("ticket") == m_ticket:
                                m_profit = float(d.get("profit", 0.0))
                                break
                    update_copied_trade(
                        master_ticket=m_ticket,
                        slave_login=s_login,
                        status="closed",
                        closed_at=now_iso,
                        slave_profit=s_profit,
                        master_profit=m_profit
                    )

        # 2. Process Master OPEN or MODIFIED positions -> Replicate to active slaves
        symbol_mappings = grp.get("symbol_mappings", {})
        copy_sl_tp = bool(grp.get("copy_sl_tp", 1))
        max_slippage = int(grp.get("max_slippage_points", 20))
        copy_pending_orders = bool(grp.get("copy_pending_orders", 1))

        for m_ticket, m_pos in curr_master_pos_map.items():
            for s in slaves:
                if s.get("status") != "active":
                    continue
                slave_login = s["slave_login"]
                slave_acc = get_account_by_login(slave_login)
                if not slave_acc:
                    continue

                slave_positions = slave_acc.get("open_positions", [])
                slave_orders = slave_acc.get("pending_orders", [])
                
                # Check if slave already holds a position (or pending order) copied from this master ticket
                existing_slave_ticket = self._find_matching_slave_ticket(
                    m_ticket, slave_login, slave_positions, slave_orders
                )

                if existing_slave_ticket:
                    is_in_positions = any(int(p.get("ticket", 0)) == existing_slave_ticket for p in slave_positions)
                    if is_in_positions:
                        update_copied_trade(master_ticket=m_ticket, slave_login=slave_login, status="open")
                        if copy_sl_tp:
                            self._check_and_dispatch_modify(
                                group_id, master_login, slave_login, m_ticket,
                                existing_slave_ticket, m_pos, slave_positions, slave_acc
                            )
                    else:
                        # Order is still pending on slave. Wait for it to trigger.
                        pass
                else:
                    # New position to copy!
                    self._dispatch_open(
                        group_id, master_login, slave_login, m_ticket, m_pos,
                        grp, s, master_acc, slave_acc, symbol_mappings, max_slippage, copy_sl_tp
                    )

        # 3. Process Master PENDING orders
        master_pending = master_acc.get("pending_orders", [])
        curr_master_pending_map = {int(o["ticket"]): o for o in master_pending if "ticket" in o}
        prev_master_pending_map = self.master_pending_cache.get(master_login, {})
        self.master_pending_cache[master_login] = curr_master_pending_map

        # 3A. Cancelled / Removed master pending orders
        for old_ticket, old_order in prev_master_pending_map.items():
            if old_ticket not in curr_master_pending_map:
                # If old_ticket transitioned into master open positions, it triggered/filled! Do not cancel.
                if old_ticket in curr_master_pos_map:
                    continue
                for s in slaves:
                    if s.get("status") != "active":
                        continue
                    slave_login = s["slave_login"]
                    self._dispatch_cancel_pending(group_id, master_login, slave_login, old_ticket, old_order)

        # 3B. New or modified master pending orders
        if copy_pending_orders:
            for m_ticket, m_order in curr_master_pending_map.items():
                for s in slaves:
                    if s.get("status") != "active":
                        continue
                    slave_login = s["slave_login"]
                    slave_acc = get_account_by_login(slave_login)
                    if not slave_acc:
                        continue

                    slave_orders = slave_acc.get("pending_orders", [])
                    slave_positions = slave_acc.get("open_positions", [])

                    existing_slave_ticket = self._find_matching_slave_pending_ticket(
                        m_ticket, slave_login, slave_orders, slave_positions
                    )

                    if existing_slave_ticket:
                        # Check for price, SL, or TP modifications
                        self._check_and_dispatch_modify_pending(
                            group_id, master_login, slave_login, m_ticket,
                            existing_slave_ticket, m_order, slave_orders, slave_acc, copy_sl_tp
                        )
                    else:
                        # New pending order to replicate
                        self._dispatch_place_pending(
                            group_id, master_login, slave_login, m_ticket, m_order,
                            grp, s, master_acc, slave_acc, symbol_mappings, max_slippage, copy_sl_tp
                        )

    def _find_matching_slave_ticket(
        self,
        master_ticket: int,
        slave_login: int,
        slave_positions: List[Dict[str, Any]],
        slave_orders: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[int]:
        # 1. Check in-memory ticket mapping
        key = (master_ticket, slave_login)
        cached_slave_ticket = self.ticket_mappings.get(key)
        if cached_slave_ticket:
            for sp in slave_positions:
                if int(sp.get("ticket", 0)) == cached_slave_ticket:
                    return cached_slave_ticket
            if slave_orders:
                for so in slave_orders:
                    if int(so.get("ticket", 0)) == cached_slave_ticket:
                        return cached_slave_ticket

        # 2. Check position comments: 'C:{master_ticket}'
        match_str = f"C:{master_ticket}"
        for sp in slave_positions:
            comment = str(sp.get("comment", "")).strip()
            if match_str in comment:
                ticket = int(sp["ticket"])
                self.ticket_mappings[key] = ticket
                return ticket

        if slave_orders:
            for so in slave_orders:
                comment = str(so.get("comment", "")).strip()
                if match_str in comment:
                    ticket = int(so["ticket"])
                    self.ticket_mappings[key] = ticket
                    return ticket

        # 3. Check DB
        db_rec = get_active_copied_trade(master_ticket, slave_login)
        if db_rec and db_rec.get("slave_ticket"):
            ticket = int(db_rec["slave_ticket"])
            self.ticket_mappings[key] = ticket
            return ticket

        return None

    def _find_matching_slave_pending_ticket(
        self,
        master_ticket: int,
        slave_login: int,
        slave_orders: List[Dict[str, Any]],
        slave_positions: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[int]:
        key = (master_ticket, slave_login)
        match_str = f"C:{master_ticket}"

        # 1. Check in-memory pending ticket mapping
        cached = self.pending_ticket_mappings.get(key)
        if cached:
            for so in slave_orders:
                if int(so.get("ticket", 0)) == cached:
                    return cached
            if slave_positions:
                for sp in slave_positions:
                    if int(sp.get("ticket", 0)) == cached:
                        return cached

        # 2. Check comments in pending orders
        for so in slave_orders:
            comment = str(so.get("comment", "")).strip()
            if match_str in comment:
                ticket = int(so["ticket"])
                self.pending_ticket_mappings[key] = ticket
                return ticket

        # 3. Check comments in open positions (in case it already filled!)
        if slave_positions:
            for sp in slave_positions:
                comment = str(sp.get("comment", "")).strip()
                if match_str in comment:
                    ticket = int(sp["ticket"])
                    return ticket

        # 4. Check DB
        db_rec = get_active_copied_trade(master_ticket, slave_login)
        if db_rec and db_rec.get("slave_ticket"):
            ticket = int(db_rec["slave_ticket"])
            self.pending_ticket_mappings[key] = ticket
            return ticket

        return None

    def _dispatch_open(
        self,
        group_id: int,
        master_login: int,
        slave_login: int,
        master_ticket: int,
        m_pos: Dict[str, Any],
        group_cfg: Dict[str, Any],
        slave_cfg: Dict[str, Any],
        master_acc: Dict[str, Any],
        slave_acc: Dict[str, Any],
        symbol_mappings: Dict[str, str],
        max_slippage: int,
        copy_sl_tp: bool
    ):
        key = (master_ticket, slave_login)
        now_ts = time.time()
        # Prevent rapid duplicate dispatches (10-second cooldown per master ticket + slave)
        if key in self.action_timestamps and (now_ts - self.action_timestamps[key]) < 10:
            return

        node_id = slave_acc.get("assigned_node_id")
        if not node_id:
            return

        master_symbol = m_pos.get("symbol", "")
        slave_symbol = self.map_symbol(master_symbol, symbol_mappings)
        order_type = str(m_pos.get("type", "BUY")).upper()
        master_vol = float(m_pos.get("volume", 0.01))

        slave_vol = self.calculate_slave_volume(
            master_vol, group_cfg, slave_cfg, master_acc, slave_acc
        )

        sl = float(m_pos.get("sl", 0.0)) if copy_sl_tp else 0.0
        tp = float(m_pos.get("tp", 0.0)) if copy_sl_tp else 0.0
        master_open_price = float(m_pos.get("price_open", 0.0))

        cmd_payload = {
            "group_id": group_id,
            "master_login": master_login,
            "slave_login": slave_login,
            "master_ticket": master_ticket,
            "symbol": slave_symbol,
            "order_type": order_type,
            "volume": slave_vol,
            "sl": sl,
            "tp": tp,
            "deviation": max_slippage,
            "master_open_price": master_open_price,
            "comment": f"C:{master_ticket}",
            "magic": 880000 + int(group_id)
        }

        self.action_timestamps[key] = now_ts
        cmd_id = enqueue_node_command(node_id, slave_login, "OPEN", cmd_payload)
        logger.info(
            f"Enqueued OPEN command {cmd_id} for Slave {slave_login} (Master #{master_ticket}, {slave_symbol} {order_type} {slave_vol} lots)"
        )

    def _check_and_dispatch_modify(
        self,
        group_id: int,
        master_login: int,
        slave_login: int,
        master_ticket: int,
        slave_ticket: int,
        m_pos: Dict[str, Any],
        slave_positions: List[Dict[str, Any]],
        slave_acc: Dict[str, Any]
    ):
        sp = next((p for p in slave_positions if int(p.get("ticket", 0)) == slave_ticket), None)
        if not sp:
            return

        m_sl = round(float(m_pos.get("sl", 0.0)), 5)
        m_tp = round(float(m_pos.get("tp", 0.0)), 5)
        s_sl = round(float(sp.get("sl", 0.0)), 5)
        s_tp = round(float(sp.get("tp", 0.0)), 5)

        # Check if SL or TP deviates significantly (more than 1 point diff)
        if abs(m_sl - s_sl) > 0.0001 or abs(m_tp - s_tp) > 0.0001:
            key = (master_ticket, slave_login, "mod")
            now_ts = time.time()
            if key in self.action_timestamps and (now_ts - self.action_timestamps[key]) < 3:
                return

            node_id = slave_acc.get("assigned_node_id")
            if not node_id:
                return

            cmd_payload = {
                "group_id": group_id,
                "master_login": master_login,
                "slave_login": slave_login,
                "master_ticket": master_ticket,
                "slave_ticket": slave_ticket,
                "symbol": sp.get("symbol", m_pos.get("symbol", "")),
                "sl": m_sl,
                "tp": m_tp
            }
            self.action_timestamps[key] = now_ts
            enqueue_node_command(node_id, slave_login, "MODIFY_SLTP", cmd_payload)
            logger.info(
                f"Enqueued MODIFY_SLTP for Slave {slave_login} Ticket #{slave_ticket} (SL: {m_sl}, TP: {m_tp})"
            )

    def _dispatch_close(
        self,
        group_id: int,
        master_login: int,
        slave_login: int,
        master_ticket: int,
        old_m_pos: Dict[str, Any]
    ):
        key = (master_ticket, slave_login)
        now_ts = time.time()
        if key in self.action_timestamps and (now_ts - self.action_timestamps[key]) < 2:
            return

        slave_acc = get_account_by_login(slave_login)
        if not slave_acc:
            return

        node_id = slave_acc.get("assigned_node_id")
        if not node_id:
            return

        slave_positions = slave_acc.get("open_positions", [])
        slave_ticket = self._find_matching_slave_ticket(master_ticket, slave_login, slave_positions)

        cmd_payload = {
            "group_id": group_id,
            "master_login": master_login,
            "slave_login": slave_login,
            "master_ticket": master_ticket,
            "slave_ticket": slave_ticket,
            "symbol": old_m_pos.get("symbol", ""),
            "order_type": old_m_pos.get("type", "BUY"),
            "volume": float(old_m_pos.get("volume", 0.01)),
            "comment": f"Close C:{master_ticket}",
            "master_profit": float(old_m_pos.get("profit", 0.0))
        }

        self.action_timestamps[key] = now_ts
        cmd_id = enqueue_node_command(node_id, slave_login, "CLOSE", cmd_payload)
        logger.info(
            f"Enqueued CLOSE command {cmd_id} for Slave {slave_login} (Master #{master_ticket}, Slave #{slave_ticket})"
        )

    def _dispatch_place_pending(
        self,
        group_id: int,
        master_login: int,
        slave_login: int,
        master_ticket: int,
        m_order: Dict[str, Any],
        group_cfg: Dict[str, Any],
        slave_cfg: Dict[str, Any],
        master_acc: Dict[str, Any],
        slave_acc: Dict[str, Any],
        symbol_mappings: Dict[str, str],
        max_slippage: int,
        copy_sl_tp: bool
    ):
        key = (master_ticket, slave_login)
        now_ts = time.time()
        # Prevent rapid duplicate dispatches
        if key in self.action_timestamps and (now_ts - self.action_timestamps[key]) < 10:
            return

        node_id = slave_acc.get("assigned_node_id")
        if not node_id:
            return

        master_symbol = m_order.get("symbol", "")
        slave_symbol = self.map_symbol(master_symbol, symbol_mappings)
        order_type = str(m_order.get("type", "BUY_LIMIT")).upper()
        master_vol = float(m_order.get("volume", 0.01))

        slave_vol = self.calculate_slave_volume(
            master_vol, group_cfg, slave_cfg, master_acc, slave_acc
        )

        price = float(m_order.get("price_open", 0.0))
        sl = float(m_order.get("sl", 0.0)) if copy_sl_tp else 0.0
        tp = float(m_order.get("tp", 0.0)) if copy_sl_tp else 0.0
        stoplimit = float(m_order.get("stoplimit", 0.0))

        cmd_payload = {
            "group_id": group_id,
            "master_login": master_login,
            "slave_login": slave_login,
            "master_ticket": master_ticket,
            "symbol": slave_symbol,
            "order_type": order_type,
            "volume": slave_vol,
            "price": price,
            "master_open_price": price,
            "sl": sl,
            "tp": tp,
            "stoplimit": stoplimit,
            "deviation": max_slippage,
            "comment": f"C:{master_ticket}",
            "magic": 880000 + int(group_id)
        }

        self.action_timestamps[key] = now_ts
        cmd_id = enqueue_node_command(node_id, slave_login, "PLACE_PENDING", cmd_payload)
        logger.info(
            f"Enqueued PLACE_PENDING command {cmd_id} for Slave {slave_login} (Master #{master_ticket}, {slave_symbol} {order_type} {slave_vol} lots at {price})"
        )

    def _check_and_dispatch_modify_pending(
        self,
        group_id: int,
        master_login: int,
        slave_login: int,
        master_ticket: int,
        slave_ticket: int,
        m_order: Dict[str, Any],
        slave_orders: List[Dict[str, Any]],
        slave_acc: Dict[str, Any],
        copy_sl_tp: bool
    ):
        so = next((o for o in slave_orders if int(o.get("ticket", 0)) == slave_ticket), None)
        if not so:
            return

        m_price = round(float(m_order.get("price_open", 0.0)), 5)
        s_price = round(float(so.get("price_open", 0.0)), 5)

        m_sl = round(float(m_order.get("sl", 0.0)), 5) if copy_sl_tp else 0.0
        m_tp = round(float(m_order.get("tp", 0.0)), 5) if copy_sl_tp else 0.0
        s_sl = round(float(so.get("sl", 0.0)), 5)
        s_tp = round(float(so.get("tp", 0.0)), 5)

        price_changed = abs(m_price - s_price) > 0.0001
        sl_tp_changed = copy_sl_tp and (abs(m_sl - s_sl) > 0.0001 or abs(m_tp - s_tp) > 0.0001)

        if price_changed or sl_tp_changed:
            key = (master_ticket, slave_login, "mod_pending")
            now_ts = time.time()
            if key in self.action_timestamps and (now_ts - self.action_timestamps[key]) < 3:
                return

            node_id = slave_acc.get("assigned_node_id")
            if not node_id:
                return

            cmd_payload = {
                "group_id": group_id,
                "master_login": master_login,
                "slave_login": slave_login,
                "master_ticket": master_ticket,
                "slave_ticket": slave_ticket,
                "symbol": so.get("symbol", m_order.get("symbol", "")),
                "price": m_price,
                "sl": m_sl,
                "tp": m_tp,
                "stoplimit": float(m_order.get("stoplimit", 0.0))
            }
            self.action_timestamps[key] = now_ts
            enqueue_node_command(node_id, slave_login, "MODIFY_PENDING", cmd_payload)
            logger.info(
                f"Enqueued MODIFY_PENDING for Slave {slave_login} Ticket #{slave_ticket} (Price: {m_price}, SL: {m_sl}, TP: {m_tp})"
            )

    def _dispatch_cancel_pending(
        self,
        group_id: int,
        master_login: int,
        slave_login: int,
        master_ticket: int,
        old_m_order: Dict[str, Any]
    ):
        key = (master_ticket, slave_login)
        now_ts = time.time()
        if key in self.action_timestamps and (now_ts - self.action_timestamps[key]) < 2:
            return

        slave_acc = get_account_by_login(slave_login)
        if not slave_acc:
            return

        node_id = slave_acc.get("assigned_node_id")
        if not node_id:
            return

        slave_orders = slave_acc.get("pending_orders", [])
        slave_positions = slave_acc.get("open_positions", [])
        slave_ticket = self._find_matching_slave_pending_ticket(
            master_ticket, slave_login, slave_orders, slave_positions
        )

        cmd_payload = {
            "group_id": group_id,
            "master_login": master_login,
            "slave_login": slave_login,
            "master_ticket": master_ticket,
            "slave_ticket": slave_ticket,
            "symbol": old_m_order.get("symbol", "")
        }

        self.action_timestamps[key] = now_ts
        cmd_id = enqueue_node_command(node_id, slave_login, "CANCEL_PENDING", cmd_payload)
        logger.info(
            f"Enqueued CANCEL_PENDING command {cmd_id} for Slave {slave_login} (Master #{master_ticket}, Slave #{slave_ticket})"
        )

    def handle_command_result(self, cmd_id: str, payload: Dict[str, Any]):
        """Processes execution result returned from a Worker Node."""
        status = payload.get("status", "failed")
        action = payload.get("action", "")
        data = payload.get("data", {})

        group_id = data.get("group_id")
        master_login = data.get("master_login")
        slave_login = data.get("slave_login")
        master_ticket = data.get("master_ticket")
        slave_ticket = data.get("slave_ticket")
        exec_ms = data.get("execution_ms", 0)

        if action == "OPEN":
            if status == "success":
                symbol = data.get("symbol", "")
                order_type = data.get("order_type", "")
                master_vol = float(data.get("master_volume", 0.0))
                slave_vol = float(data.get("slave_volume", 0.0))
                master_price = float(data.get("master_open_price", 0.0))
                slave_price = float(data.get("slave_open_price", 0.0))

                if master_ticket and slave_ticket:
                    existing = get_active_copied_trade(master_ticket, slave_login)
                    if existing:
                        logger.warning(
                            f"Active copied trade already recorded for Master #{master_ticket} -> Slave {slave_login} (Existing Slave #{existing.get('slave_ticket')}). Skipping duplicate record."
                        )
                        return

                    self.ticket_mappings[(master_ticket, slave_login)] = slave_ticket
                    record_copied_trade(
                        group_id=group_id,
                        master_login=master_login,
                        slave_login=slave_login,
                        master_ticket=master_ticket,
                        slave_ticket=slave_ticket,
                        symbol=symbol,
                        order_type=order_type,
                        master_volume=master_vol,
                        slave_volume=slave_vol,
                        master_open_price=master_price,
                        slave_open_price=slave_price,
                        execution_ms=exec_ms
                    )
                    add_log(f"Trade #{master_ticket} copied to Slave {slave_login} Ticket #{slave_ticket} ({symbol} {order_type} {slave_vol}L in {exec_ms}ms).", source="COPIER")
            else:
                err_msg = payload.get("error", "Unknown error")
                add_log(f"Copy trade #{master_ticket} failed on Slave {slave_login}: {err_msg}", level="WARNING", source="COPIER")

        elif action in ("PLACE_PENDING", "PENDING"):
            if status == "success":
                symbol = data.get("symbol", "")
                order_type = data.get("order_type", "")
                master_vol = float(data.get("master_volume", 0.0))
                slave_vol = float(data.get("slave_volume", 0.0))
                master_price = float(data.get("master_open_price", 0.0))
                slave_price = float(data.get("slave_open_price", master_price))

                if master_ticket and slave_ticket:
                    existing = get_active_copied_trade(master_ticket, slave_login)
                    if existing:
                        logger.warning(
                            f"Active copied trade already recorded for Master #{master_ticket} -> Slave {slave_login}. Skipping duplicate record."
                        )
                        return

                    self.pending_ticket_mappings[(master_ticket, slave_login)] = slave_ticket
                    self.ticket_mappings[(master_ticket, slave_login)] = slave_ticket
                    record_copied_trade(
                        group_id=group_id,
                        master_login=master_login,
                        slave_login=slave_login,
                        master_ticket=master_ticket,
                        slave_ticket=slave_ticket,
                        symbol=symbol,
                        order_type=order_type,
                        master_volume=master_vol,
                        slave_volume=slave_vol,
                        master_open_price=master_price,
                        slave_open_price=slave_price,
                        execution_ms=exec_ms,
                        status="pending"
                    )
                    add_log(f"Pending order #{master_ticket} copied to Slave {slave_login} Ticket #{slave_ticket} ({symbol} {order_type} {slave_vol}L at {slave_price} in {exec_ms}ms).", source="COPIER")
            else:
                err_msg = payload.get("error", "Unknown error")
                add_log(f"Copy pending order #{master_ticket} failed on Slave {slave_login}: {err_msg}", level="WARNING", source="COPIER")

        elif action == "CLOSE":
            now_iso = datetime.now(timezone.utc).isoformat()
            slave_profit = float(data.get("profit", 0.0))
            master_profit = float(payload.get("master_profit", 0.0))
            close_update_fields = {
                "status": "closed",
                "closed_at": now_iso,
                "slave_profit": slave_profit
            }
            if master_profit != 0.0:
                close_update_fields["master_profit"] = master_profit

            update_copied_trade(
                master_ticket=master_ticket,
                slave_login=slave_login,
                **close_update_fields
            )
            # Remove mapping
            self.ticket_mappings.pop((master_ticket, slave_login), None)
            self.pending_ticket_mappings.pop((master_ticket, slave_login), None)
            if status == "success":
                add_log(f"Closed trade #{slave_ticket} on Slave {slave_login} (Master #{master_ticket}, Profit: ${slave_profit:.2f}).", source="COPIER")

        elif action in ("CANCEL_PENDING", "DELETE_PENDING"):
            now_iso = datetime.now(timezone.utc).isoformat()
            update_copied_trade(
                master_ticket=master_ticket,
                slave_login=slave_login,
                status="cancelled",
                closed_at=now_iso
            )
            self.pending_ticket_mappings.pop((master_ticket, slave_login), None)
            self.ticket_mappings.pop((master_ticket, slave_login), None)
            if status == "success":
                add_log(f"Cancelled pending order on Slave {slave_login} (Master #{master_ticket}).", source="COPIER")

copier_engine = TradeCopierEngine()
