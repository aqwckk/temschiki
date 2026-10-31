"""Журнал прогонов сценариев и уведомления."""
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import Notification, ScenarioRun
from app.realtime import events
from app.schemas import NotificationRead, ScenarioRunRead


def save_run(
    scenario_id: int,
    cause: str,
    status: str,
    reason: str,
    steps: list[dict],
    started_at: datetime,
) -> None:
    with SessionLocal() as session:
        run = ScenarioRun(
            scenario_id=scenario_id,
            cause=cause,
            status=status,
            reason=reason,
            steps=steps,
            started_at=started_at,
        )
        session.add(run)
        session.commit()
        events.publish_run(ScenarioRunRead.model_validate(run).model_dump(mode="json"))


def add_notification(target: str, message: str, scenario_id: Optional[int] = None) -> None:
    with SessionLocal() as session:
        notification = Notification(target=target, message=message, scenario_id=scenario_id)
        session.add(notification)
        session.commit()
        events.publish_notification(NotificationRead.model_validate(notification).model_dump(mode="json"))


def list_runs(session: Session, scenario_id: Optional[int] = None, limit: int = 50) -> list[ScenarioRun]:
    query = select(ScenarioRun).order_by(ScenarioRun.id.desc()).limit(limit)
    if scenario_id is not None:
        query = query.where(ScenarioRun.scenario_id == scenario_id)
    return list(session.scalars(query))


def list_notifications(session: Session, target: Optional[str] = None, limit: int = 50) -> list[Notification]:
    query = select(Notification).order_by(Notification.id.desc()).limit(limit)
    if target is not None:
        query = query.where(Notification.target == target)
    return list(session.scalars(query))
