from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.emulation.runtime import runtime
from app.models import Device
from app.schemas import (
    CommandIn,
    DeviceCreate,
    DeviceRead,
    DeviceState,
    DeviceUpdate,
    PowerIn,
    SimulateIn,
)
from app.services import devices as service

router = APIRouter(prefix="/api/devices", tags=["devices"])


def get_existing_device(device_id: int, session: Session = Depends(get_session)) -> Device:
    device = service.get_device(session, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="устройство не найдено")
    return device


def to_read(device: Device) -> DeviceRead:
    data = DeviceRead.model_validate(device)
    data.online = runtime.is_online(device.id)
    return data


def to_state(device: Device) -> DeviceState:
    return DeviceState(
        device_id=device.id,
        online=runtime.is_online(device.id),
        values=runtime.values(device.id),
    )


@router.get("", response_model=list[DeviceRead])
def list_devices(session: Session = Depends(get_session)):
    return [to_read(device) for device in service.list_devices(session)]


@router.get("/{device_id}", response_model=DeviceRead)
def get_device(device: Device = Depends(get_existing_device)):
    return to_read(device)


@router.post("", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
def create_device(data: DeviceCreate, session: Session = Depends(get_session)):
    return to_read(service.create_device(session, data))


@router.patch("/{device_id}", response_model=DeviceRead)
def update_device(
    data: DeviceUpdate,
    device: Device = Depends(get_existing_device),
    session: Session = Depends(get_session),
):
    return to_read(service.update_device(session, device, data))


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device: Device = Depends(get_existing_device),
    session: Session = Depends(get_session),
):
    service.delete_device(session, device)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{device_id}/state", response_model=DeviceState)
def get_state(device: Device = Depends(get_existing_device)):
    return to_state(device)


@router.post("/{device_id}/command", response_model=DeviceState)
def send_command(data: CommandIn, device: Device = Depends(get_existing_device)):
    runtime.command(device.id, data.signal, data.value)
    return to_state(device)


@router.post("/{device_id}/simulate", response_model=DeviceState)
def simulate(data: SimulateIn, device: Device = Depends(get_existing_device)):
    runtime.simulate(device.id, data.input, data.value)
    return to_state(device)


@router.put("/{device_id}/power", response_model=DeviceState)
def set_power(data: PowerIn, device: Device = Depends(get_existing_device)):
    runtime.set_online(device.id, data.online)
    return to_state(device)
