from fastapi import APIRouter

from app.schemas import UjinStatus
from app.ujin.mirror import mirror

router = APIRouter(prefix="/api/ujin", tags=["ujin"])


@router.get("/status", response_model=UjinStatus)
def get_status():
    return mirror.status()
