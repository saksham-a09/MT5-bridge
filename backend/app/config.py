import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present
base_dir = Path(__file__).resolve().parent.parent
data_dir = base_dir / "data"
data_dir.mkdir(parents=True, exist_ok=True)

load_dotenv(base_dir / ".env")

class Settings:
    APP_NAME: str = "Dashboard API"
    HOST: str = os.getenv("HUB_HOST", "0.0.0.0")
    PORT: int = int(os.getenv("HUB_PORT", "8000"))
    DATABASE_PATH: str = os.getenv("HUB_DB_PATH", str(data_dir / "hub.db"))
    SECRET_KEY: str = os.getenv("HUB_SECRET_KEY", "cluster-secret-key-2026")
    DEFAULT_MASTER_MT5_DIR: str = os.getenv("MASTER_MT5_DIR", r"E:\MT5 instances\Master MT5")
    HEARTBEAT_TIMEOUT_SECONDS: int = int(os.getenv("HEARTBEAT_TIMEOUT_SECONDS", "30"))
    CORS_ORIGINS: list[str] = ["*"]

settings = Settings()
