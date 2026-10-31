from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Device
from app.schemas import DeviceCreate, DeviceUpdate


def list_devices(session: Session) -> list[Device]:
    return list(session.scalars(select(Device).order_by(Device.id)))


def get_device(session: Session, device_id: int) -> Optional[Device]:
    return session.get(Device, device_id)


def create_device(session: Session, data: DeviceCreate) -> Device:
    device = Device(name=data.name, family=data.family)
    session.add(device)
    session.commit()
    return device


def update_device(session: Session, device: Device, data: DeviceUpdate) -> Device:
    device.name = data.name
    session.commit()
    return device


def delete_device(session: Session, device: Device) -> None:
    session.delete(device)
    session.commit()
