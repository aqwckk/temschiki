from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Device
from app.schemas import DeviceCreate, DeviceRead, DeviceUpdate
from app.services import devices as service

router = APIRouter(prefix="/api/devices", tags=["devices"])


def get_existing_device(device_id: int, session: Session = Depends(get_session)) -> Device:
    device = service.get_device(session, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="устройство не найдено")
    return device


@router.get("", response_model=list[DeviceRead])
def list_devices(session: Session = Depends(get_session)):
    return service.list_devices(session)


@router.get("/{device_id}", response_model=DeviceRead)
def get_device(device: Device = Depends(get_existing_device)):
    return device


@router.post("", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
def create_device(data: DeviceCreate, session: Session = Depends(get_session)):
    return service.create_device(session, data)


@router.patch("/{device_id}", response_model=DeviceRead)
def update_device(
    data: DeviceUpdate,
    device: Device = Depends(get_existing_device),
    session: Session = Depends(get_session),
):
    return service.update_device(session, device, data)


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device(
    device: Device = Depends(get_existing_device),
    session: Session = Depends(get_session),
):
    service.delete_device(session, device)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
