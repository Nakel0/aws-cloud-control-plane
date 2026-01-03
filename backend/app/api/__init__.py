from fastapi import APIRouter
from app.api.endpoints import onboard, scan

router = APIRouter()

router.include_router(onboard.router, prefix="/onboard", tags=["Onboarding"])
router.include_router(scan.router, prefix="/scan", tags=["Scanning"])
