from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class AccountCreate(BaseModel):
    login: int = Field(..., description="MT5 Account Login ID")
    password: str = Field(..., description="MT5 Account Password")
    server: str = Field(..., description="Broker Server Name (e.g. VantageMarkets-Demo)")
    name: Optional[str] = Field(default="", description="Display label / user name")
    target_node_id: Optional[str] = Field(default="auto", description="'auto' or specific Worker Node ID")
    expert: Optional[str] = Field(default="", description="Expert Advisor name (optional)")
    symbol: Optional[str] = Field(default="", description="Trading symbol (optional)")
    timeframe: Optional[str] = Field(default="", description="Timeframe (optional)")

class AccountBulkCreate(BaseModel):
    accounts: List[AccountCreate] = Field(..., description="List of MT5 accounts to create or update")
    overwrite_existing: Optional[bool] = Field(default=True, description="Whether to update fields if login already exists")

class AccountUpdate(BaseModel):
    password: Optional[str] = None
    server: Optional[str] = None
    name: Optional[str] = None
    status: Optional[str] = None
    target_node_id: Optional[str] = None
    expert: Optional[str] = None
    symbol: Optional[str] = None
    timeframe: Optional[str] = None

class NodeRegister(BaseModel):
    node_id: str = Field(..., description="Unique Hardware Node Identifier (e.g. vps-ny-01)")
    name: str = Field(..., description="Friendly Name for this hardware/VPS")
    api_key: str = Field(..., description="Authentication secret key")
    ip_address: Optional[str] = Field(default="")
    max_terminals: Optional[int] = Field(default=25, description="Max MT5 terminals this hardware can run")
    os_info: Optional[str] = Field(default="")

class NodeHeartbeat(BaseModel):
    cpu_percent: float = Field(default=0.0)
    ram_percent: float = Field(default=0.0)
    ram_used_mb: float = Field(default=0.0)
    ram_total_mb: float = Field(default=0.0)
    active_terminals: int = Field(default=0)
    ip_address: Optional[str] = Field(default="")

class SingleTerminalTelemetry(BaseModel):
    login: int
    is_connected: bool = False
    broker_name: Optional[str] = ""
    server: Optional[str] = ""
    currency: Optional[str] = "USD"
    leverage: Optional[int] = 100
    balance: Optional[float] = 0.0
    equity: Optional[float] = 0.0
    profit: Optional[float] = 0.0
    margin: Optional[float] = 0.0
    margin_free: Optional[float] = 0.0
    margin_level: Optional[float] = 0.0
    ping: Optional[int] = 0
    daily_closed_pnl: Optional[float] = 0.0
    open_positions: Optional[List[Dict[str, Any]]] = []
    pending_orders: Optional[List[Dict[str, Any]]] = []
    deals_history: Optional[List[Dict[str, Any]]] = []
    error_message: Optional[str] = ""

class BatchTelemetry(BaseModel):
    terminals: List[SingleTerminalTelemetry]

class CopyGroupCreate(BaseModel):
    name: str = Field(..., description="Copy Group Name")
    master_login: int = Field(..., description="Master MT5 Account Login")
    risk_type: Optional[str] = Field(default="multiplier", description="'multiplier', 'equity_ratio', 'balance_ratio', 'fixed_lot'")
    multiplier: Optional[float] = Field(default=1.0, description="Volume multiplier (for 'multiplier' mode)")
    fixed_lot: Optional[float] = Field(default=0.01, description="Fixed volume lot (for 'fixed_lot' mode)")
    max_slippage_points: Optional[int] = Field(default=20, description="Max acceptable slippage in points")
    copy_sl_tp: Optional[bool] = Field(default=True, description="Whether to copy SL and TP")
    copy_pending_orders: Optional[bool] = Field(default=True, description="Whether to copy pending orders")
    symbol_mappings: Optional[Dict[str, str]] = Field(default={}, description="Symbol name translations, e.g. {'XAUUSD': 'GOLD'}")
    initial_slave_logins: Optional[List[int]] = Field(default=[], description="List of slave logins to add immediately")

class CopyGroupUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    risk_type: Optional[str] = None
    multiplier: Optional[float] = None
    fixed_lot: Optional[float] = None
    max_slippage_points: Optional[int] = None
    copy_sl_tp: Optional[bool] = None
    copy_pending_orders: Optional[bool] = None
    symbol_mappings: Optional[Dict[str, str]] = None

class SlaveAdd(BaseModel):
    slave_login: int = Field(..., description="Slave MT5 Account Login to add")
    custom_multiplier: Optional[float] = Field(default=None, description="Optional override multiplier")
    custom_fixed_lot: Optional[float] = Field(default=None, description="Optional override fixed lot")

class TradeCommandResult(BaseModel):
    command_id: str
    status: str  # 'success', 'failed'
    result: Dict[str, Any]

