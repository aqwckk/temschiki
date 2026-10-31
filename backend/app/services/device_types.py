"""Типы устройств из конструктора: хранятся в базе, работают через реестр."""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.emulation import registry
from app.emulation.errors import DeviceTypeConflict
from app.emulation.runtime import runtime
from app.emulation.spec import DeviceTypeSpec
from app.models import CustomDeviceType, Device
from app.scenarios.engine import engine


def to_spec(row: CustomDeviceType) -> DeviceTypeSpec:
    return DeviceTypeSpec(family=row.family, title=row.title, signals=row.signals)


def get_custom(session: Session, family: str) -> Optional[CustomDeviceType]:
    return session.scalar(select(CustomDeviceType).where(CustomDeviceType.family == family))


def register_all(session: Session) -> None:
    # при старте сервера типы из базы попадают в реестр раньше устройств
    for row in session.scalars(select(CustomDeviceType)):
        registry.register_custom(to_spec(row))


def create_type(session: Session, spec: DeviceTypeSpec) -> None:
    if registry.is_known(spec.family):
        raise DeviceTypeConflict(f"тип {spec.family} уже существует")
    row = CustomDeviceType(family=spec.family, title=spec.title, signals=_dump_signals(spec))
    session.add(row)
    session.commit()
    registry.register_custom(spec)


def update_type(session: Session, row: CustomDeviceType, spec: DeviceTypeSpec) -> None:
    if spec.family != row.family:
        raise DeviceTypeConflict("имя типа менять нельзя, создайте новый тип")
    row.title = spec.title
    row.signals = _dump_signals(spec)
    session.commit()
    registry.register_custom(spec)
    # эмуляторы этого типа пересоздаются с новым набором сигналов
    for device in _devices_of(session, row.family):
        engine.forget_device(device.id)
        runtime.add(device.id, device.family)


def delete_type(session: Session, row: CustomDeviceType) -> None:
    if _devices_of(session, row.family):
        raise DeviceTypeConflict(f"тип {row.family} используется устройствами, сначала удалите их")
    session.delete(row)
    session.commit()
    registry.unregister_custom(row.family)


def _devices_of(session: Session, family: str) -> list[Device]:
    return list(session.scalars(select(Device).where(Device.family == family)))


def _dump_signals(spec: DeviceTypeSpec) -> list[dict]:
    return [signal.model_dump(mode="json") for signal in spec.signals]
