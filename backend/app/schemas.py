from datetime import datetime
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.emulation import registry
from app.scenarios.blocks import ACTION_KINDS, Block


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
    default: Optional[Union[int, float]] = None
    affects: Optional[str] = None


class InputDeclaration(BaseModel):
    name: str
    title: str
    value_type: Literal["bool", "number"]


class DeviceType(BaseModel):
    family: str
    title: str
    builtin: bool
    signals: list[SignalDeclaration]
    inputs: list[InputDeclaration]


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
    online: bool = False


class DeviceState(BaseModel):
    device_id: int
    online: bool
    values: dict[str, Any]


class CommandIn(BaseModel):
    signal: str = Field(min_length=1)
    value: Union[int, float]


class SimulateIn(BaseModel):
    input: str = Field(min_length=1)
    value: Union[int, float]


class PowerIn(BaseModel):
    online: bool


class ScenarioIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=100)
    enabled: bool = True
    blocks: list[Block]

    @model_validator(mode="after")
    def needs_trigger_and_action(self):
        kinds = [block.kind for block in self.blocks]
        if "trigger" not in kinds:
            raise ValueError("в сценарии нужен хотя бы один блок trigger")
        if not any(kind in ACTION_KINDS for kind in kinds):
            raise ValueError("в сценарии нужно хотя бы одно действие")
        return self


class ScenarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    enabled: bool
    blocks: list[Block]
    created_at: datetime


class RunStep(BaseModel):
    block_id: str
    kind: str
    ok: bool
    error: str = ""


class ScenarioRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scenario_id: int
    cause: str
    status: Literal["success", "failed", "skipped"]
    reason: str
    steps: list[RunStep]
    started_at: datetime
    finished_at: datetime


class UjinBinding(BaseModel):
    device_id: int
    family: str
    ext: str
    serialnumber: str


class UjinStatus(BaseModel):
    mode: Literal["dry", "live"]
    enabled: bool
    bindings: list[UjinBinding]
    published: int
    last_flush_at: Optional[datetime]
    last_error: str


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target: str
    message: str
    scenario_id: Optional[int]
    created_at: datetime
