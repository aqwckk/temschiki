from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_session
from app.schemas import NotificationRead, ScenarioRunRead
from app.services import journal

router = APIRouter(prefix="/api", tags=["journal"])


@router.get("/runs", response_model=list[ScenarioRunRead])
def list_runs(
    limit: int = Query(default=50, ge=1, le=500),
    session: Session = Depends(get_session),
):
    return journal.list_runs(session, limit=limit)


@router.get("/notifications", response_model=list[NotificationRead])
def list_notifications(
    target: Optional[Literal["concierge", "resident"]] = None,
    limit: int = Query(default=50, ge=1, le=500),
    session: Session = Depends(get_session),
):
    return journal.list_notifications(session, target=target, limit=limit)
