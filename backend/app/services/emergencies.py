"""Экстренные ситуации, которые житель запускает вручную на срок."""
import logging
import threading
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.emulation.runtime import runtime
from app.models import Emergency, as_utc, utcnow
from app.realtime import events
from app.schemas import EmergencyIn, EmergencyRead
from app.situations.errors import SituationInvalid
from app.services import situations as situation_service
from app.situations import catalog

logger = logging.getLogger(__name__)

DURATION_UNITS = {"h": timedelta(hours=1), "d": timedelta(days=1)}


class EmergencyBoard:
    """Активные ситуации в памяти, чтобы движок не ходил в базу каждую секунду."""

    def __init__(self):
        self._items: dict[int, tuple[str, datetime]] = {}
        self._lock = threading.Lock()

    def put(self, emergency_id: int, type_: str, ends_at: datetime) -> None:
        with self._lock:
            self._items[emergency_id] = (type_, as_utc(ends_at))

    def drop(self, emergency_id: int) -> None:
        with self._lock:
            self._items.pop(emergency_id, None)

    def active_types(self) -> set[str]:
        with self._lock:
            return {type_ for type_, _ in self._items.values()}

    def expired_ids(self, now: datetime) -> list[int]:
        with self._lock:
            return [emergency_id for emergency_id, (_, ends_at) in self._items.items() if ends_at <= now]

    def clear(self) -> None:
        with self._lock:
            self._items.clear()


board = EmergencyBoard()


def load_all(session: Session) -> None:
    board.clear()
    now = utcnow()
    for row in list_active(session):
        if as_utc(row.ends_at) <= now:
            session.delete(row)
            continue
        board.put(row.id, row.type, row.ends_at)
    session.commit()


def list_active(session: Session) -> list[Emergency]:
    return list(session.scalars(select(Emergency).order_by(Emergency.id)))


def get(session: Session, emergency_id: int) -> Optional[Emergency]:
    return session.get(Emergency, emergency_id)


def start(session: Session, data: EmergencyIn) -> Emergency:
    if data.type == "__custom":
        if not data.name:
            raise SituationInvalid("для своей ситуации нужно название")
        situation = situation_service.get_or_create(session, data.name)
    else:
        situation = catalog.find(data.type)
    if situation is None:
        raise SituationInvalid(f"неизвестная ситуация {data.type}")

    started_at = utcnow()
    row = Emergency(
        type=situation.type,
        label=situation.label,
        amount=data.amount,
        unit=data.unit,
        started_at=started_at,
        ends_at=started_at + DURATION_UNITS[data.unit] * data.amount,
    )
    session.add(row)
    session.commit()
    board.put(row.id, row.type, row.ends_at)
    _emulate(situation, on=True)
    events.publish_emergency(EmergencyRead.model_validate(row).model_dump(mode="json"))
    return row


def end(session: Session, row: Emergency) -> None:
    board.drop(row.id)
    session.delete(row)
    session.commit()
    situation = catalog.find(row.type)
    if situation is not None and row.type not in board.active_types():
        _emulate(situation, on=False)
    events.publish_emergency_ended(row.id)


def expire_due() -> None:
    """Завершает ситуации, у которых вышел срок. Вызывается движком раз в секунду."""
    due = board.expired_ids(utcnow())
    if not due:
        return
    with SessionLocal() as session:
        for emergency_id in due:
            row = session.get(Emergency, emergency_id)
            if row is None:
                board.drop(emergency_id)
                continue
            end(session, row)


def _emulate(situation, on: bool) -> None:
    # ручной запуск "Протечки" мочит все датчики протечки - цепочка видна целиком
    for emulation in situation.emulations:
        if on:
            value = emulation.on_value
        else:
            value = emulation.off_value
        for state in runtime.all_states():
            if state["family"] != emulation.family or not state["online"]:
                continue
            try:
                runtime.simulate(state["device_id"], emulation.input, value)
            except Exception as exc:
                logger.warning("не удалось изобразить ситуацию %s: %s", situation.type, exc)
