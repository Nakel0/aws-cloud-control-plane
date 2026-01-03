from fastapi import APIRouter

router = APIRouter()

@router.post("/start")
async def start_scan(account_id: str):
    """
    Trigger a scan for Waste, Security, and Reliability.
    """
    return {"status": "started", "scan_id": "scan_12345"}
