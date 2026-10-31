from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.emulation import registry


class SignalDeclaration(BaseModel):
    name: str
    title: str
    control: str
    management: Literal["r", "rw", "w"]
    kind: str
    group: Literal["property", "capability", "setting"]
    measure: Optional[str] = None
    min: Optional[float] = None
    max: Optional[float] = None
    layout: Optional[dict[str, str]] = None


class DeviceType(BaseModel):
    family: str
    title: str
    signals: list[SignalDeclaration]


class DeviceCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    family: str

    @field_validator("family")
    @classmethod
    def family_must_exist(cls, value: str) -> str:
        if not registry.is_known(value):
            raise ValueError(f"неизвестное семейство устройства: {value}")
        return value


class DeviceUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)


class DeviceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    family: str
    created_at: datetime
