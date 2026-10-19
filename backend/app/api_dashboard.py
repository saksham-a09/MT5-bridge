from fastapi import APIRouter, Query
from typing import Optional
from .db import get_dashboard_summary, get_logs

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/stats")
def dashboard_stats():
    return {
        "success": True,
        "data": get_dashboard_summary()
    }

@router.get("/logs")
def system_logs(limit: int = Query(50, ge=1, le=200)):
    return {
        "success": True,
        "logs": get_logs(limit=limit)
    }
