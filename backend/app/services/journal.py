"""Журнал прогонов сценариев."""
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import ScenarioRun
from app.realtime import events
from app.schemas import ScenarioRunRead


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


def list_runs(session: Session, scenario_id: Optional[int] = None, limit: int = 50) -> list[ScenarioRun]:
    query = select(ScenarioRun).order_by(ScenarioRun.id.desc()).limit(limit)
    if scenario_id is not None:
        query = query.where(ScenarioRun.scenario_id == scenario_id)
    return list(session.scalars(query))
