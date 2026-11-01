from datetime import datetime
from typing import Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.emulation import registry
from app.scenarios.blocks import Block, SituationCondition


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
    default: Optional[Union[int, float, str]] = None
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
    on: bool = False
    params: list[str] = []
    # текущие значения сигналов, фронт строит из них редактируемые параметры
    values: dict[str, Any] = {}


class ToggleIn(BaseModel):
    # без значения переключает в противоположное состояние
    on: Optional[bool] = None


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

    # пустой сценарий допустим: фронт создает его сразу и наполняет перетаскиванием
    title: str = Field(min_length=1, max_length=100)
    enabled: bool = True
    blocks: list[Block] = []
    conditions: list[SituationCondition] = []


class ScenarioRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    enabled: bool
    position: int
    blocks: list[Block]
    conditions: list[SituationCondition]
    created_at: datetime


class ScenarioOrder(BaseModel):
    ids: list[int]


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


class SituationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: str
    label: str
    unit: Optional[str] = None
    value: Optional[float] = None
    no_time: bool = Field(default=False, serialization_alias="noTime")
    alarm: bool = False
    custom: bool = False


class SituationCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    label: str = Field(min_length=1, max_length=40)


class EmergencyIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    # "__custom" вместе с name создает свою ситуацию, как на главной фронта
    type: str = Field(min_length=1)
    name: Optional[str] = Field(default=None, max_length=40)
    amount: int = Field(ge=1, le=365)
    unit: Literal["h", "d"]


class EmergencyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    label: str
    amount: int
    unit: str
    started_at: datetime
    ends_at: datetime


class UjinBinding(BaseModel):
    device_id: int
    family: str
    ext: str
    serialnumber: str
    # что стенд отдает по устройству через get-device-info
    remote: dict[str, Any] = {}


class UjinStatus(BaseModel):
    mode: Literal["dry", "live"]
    enabled: bool
    auth: str = ""
    bindings: list[UjinBinding]
    published: int
    last_flush_at: Optional[datetime]
    last_readback_at: Optional[datetime] = None
    commands_applied: int = 0
    last_command: str = ""
    last_error: str


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target: str
    message: str
    scenario_id: Optional[int]
    created_at: datetime
