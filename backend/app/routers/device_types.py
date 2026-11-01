from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.emulation import registry
from app.emulation.spec import DeviceTypeSpec
from app.models import CustomDeviceType
from app.schemas import DeviceType
from app.services import device_types as service

router = APIRouter(prefix="/api/device-types", tags=["device-types"])


def get_custom_type(family: str, session: Session = Depends(get_session)) -> CustomDeviceType:
    if registry.is_builtin(family):
        raise HTTPException(status_code=403, detail="готовые семейства менять нельзя")
    row = service.get_custom(session, family)
    if row is None:
        raise HTTPException(status_code=404, detail="тип устройства не найден")
    return row


@router.get("", response_model=list[DeviceType])
def list_device_types():
    return [registry.describe(family) for family in registry.families()]


@router.get("/{family}", response_model=DeviceType)
def get_device_type(family: str):
    if not registry.is_known(family):
        raise HTTPException(status_code=404, detail="тип устройства не найден")
    return registry.describe(family)


@router.post("", response_model=DeviceType, status_code=status.HTTP_201_CREATED)
def create_device_type(spec: DeviceTypeSpec, session: Session = Depends(get_session)):
    service.create_type(session, spec)
    return registry.describe(spec.family)


@router.put("/{family}", response_model=DeviceType)
def update_device_type(
    spec: DeviceTypeSpec,
    row: CustomDeviceType = Depends(get_custom_type),
    session: Session = Depends(get_session),
):
    service.update_type(session, row, spec)
    return registry.describe(spec.family)


@router.delete("/{family}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device_type(
    row: CustomDeviceType = Depends(get_custom_type),
    session: Session = Depends(get_session),
):
    service.delete_type(session, row)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
