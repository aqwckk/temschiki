from fastapi import APIRouter, HTTPException

from app.emulation import registry
from app.schemas import DeviceType

router = APIRouter(prefix="/api/device-types", tags=["device-types"])


@router.get("", response_model=list[DeviceType])
def list_device_types():
    return [registry.describe(family) for family in registry.families()]


@router.get("/{family}", response_model=DeviceType)
def get_device_type(family: str):
    if not registry.is_known(family):
        raise HTTPException(status_code=404, detail="тип устройства не найден")
    return registry.describe(family)
