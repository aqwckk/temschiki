"""Свои ситуации жителя: хранятся в базе, работают через каталог."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CustomSituation
from app.situations import catalog
from app.situations.catalog import Situation


def register_all(session: Session) -> None:
    for row in session.scalars(select(CustomSituation)):
        catalog.register_custom(row.type, row.label)


def get_or_create(session: Session, label: str) -> Situation:
    # как на фронте: ситуация с таким же названием не дублируется
    existing = catalog.find_by_label(label)
    if existing is not None:
        return existing
    row = CustomSituation(type="", label=label)
    session.add(row)
    session.flush()
    row.type = f"custom_{row.id}"
    session.commit()
    return catalog.register_custom(row.type, row.label)
