from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import ScenarioRunRead
from app.services import journal

router = APIRouter(prefix="/api", tags=["journal"])


@router.get("/runs", response_model=list[ScenarioRunRead])
def list_runs(
    limit: int = Query(default=50, ge=1, le=500),
    session: Session = Depends(get_session),
):
    return journal.list_runs(session, limit=limit)
