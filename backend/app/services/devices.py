from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.emulation.runtime import runtime
from app.scenarios.engine import engine
from app.models import Device
from app.realtime import events
from app.schemas import DeviceCreate, DeviceUpdate
from app.ujin.mirror import mirror


def list_devices(session: Session) -> list[Device]:
    return list(session.scalars(select(Device).order_by(Device.id)))


def get_device(session: Session, device_id: int) -> Optional[Device]:
    return session.get(Device, device_id)


def create_device(session: Session, data: DeviceCreate) -> Device:
    device = Device(name=data.name, family=data.family)
    session.add(device)
    session.commit()
    engine.forget_device(device.id)
    _start(device)
    return device


def update_device(session: Session, device: Device, data: DeviceUpdate) -> Device:
    device.name = data.name
    session.commit()
    return device


def delete_device(session: Session, device: Device) -> None:
    runtime.remove(device.id)
    mirror.unbind(device.id)
    engine.forget_device(device.id)
    session.delete(device)
    session.commit()


def set_power(device: Device, online: bool) -> None:
    runtime.set_online(device.id, online)
    events.publish_device_status(device.id, online)


def start_all(session: Session) -> None:
    # при старте сервера поднимаем эмуляторы всех устройств из базы
    for device in list_devices(session):
        _start(device)


def _start(device: Device) -> None:
    runtime.add(device.id, device.family)
    mirror.bind(device.id, device.family, runtime.values(device.id))
