"""Блоки сценария. Порядок блоков задает пользователь перетаскиванием."""
import operator
from typing import Annotated, Any, Literal, Optional, Union
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Discriminator, Field, Tag, field_validator

Operator = Literal["==", "!=", ">", ">=", "<", "<="]

OPERATORS = {
    "==": operator.eq,
    "!=": operator.ne,
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
}


def new_block_id() -> str:
    return uuid4().hex[:8]


def compare(left: Any, op: str, right: Any) -> bool:
    if left is None:
        return False
    try:
        return OPERATORS[op](left, right)
    except TypeError:
        return False


class SignalCheck(BaseModel):
    id: str = Field(default_factory=new_block_id)
    device_id: int
    signal: str = Field(min_length=1)
    op: Operator = "=="
    value: Union[int, float]


class TriggerBlock(SignalCheck):
    kind: Literal["trigger"]


class ConditionBlock(SignalCheck):
    kind: Literal["condition"]


class CommandBlock(BaseModel):
    id: str = Field(default_factory=new_block_id)
    kind: Literal["command"]
    device_id: int
    signal: str = Field(min_length=1)
    value: Union[int, float]


class NotifyBlock(BaseModel):
    id: str = Field(default_factory=new_block_id)
    kind: Literal["notify"]
    target: Literal["concierge", "resident"]
    message: str = Field(min_length=1, max_length=300)


class DelayBlock(BaseModel):
    id: str = Field(default_factory=new_block_id)
    kind: Literal["delay"]
    seconds: float = Field(gt=0, le=300)


class DeviceBlock(BaseModel):
    """Блок фронта: устройство из панели. Выполняется главной командой устройства."""

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=new_block_id)
    kind: Literal["device"] = "device"
    device_id: int = Field(alias="deviceId")
    on: bool = True
    # блоки с одинаковым col выполняются одновременно
    col: Optional[int] = None


def _block_kind(data: Any) -> str:
    # фронт присылает блок устройства без kind
    if isinstance(data, dict):
        return data.get("kind", "device")
    return getattr(data, "kind", "device")


Block = Annotated[
    Union[
        Annotated[TriggerBlock, Tag("trigger")],
        Annotated[ConditionBlock, Tag("condition")],
        Annotated[CommandBlock, Tag("command")],
        Annotated[NotifyBlock, Tag("notify")],
        Annotated[DelayBlock, Tag("delay")],
        Annotated[DeviceBlock, Tag("device")],
    ],
    Discriminator(_block_kind),
]

ACTION_KINDS = ("device", "command", "notify", "delay")


Reaction = Literal["off", "on", "notify", "support", "none", "custom"]


class SituationCondition(BaseModel):
    """Ситуация, влияющая на сценарий. Время - необязательное "во сколько".

    action - что сделать, когда ситуация началась: выключить или включить устройства
    сценария, прислать уведомление, обратиться в техподдержку, ничего или свое действие.
    """

    model_config = ConfigDict(populate_by_name=True)

    id: str = Field(default_factory=new_block_id)
    type: str = Field(min_length=1)
    time: Optional[str] = Field(default=None, pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    value: Optional[float] = None
    action: Reaction = "off"
    action_text: str = Field(default="", alias="actionText", max_length=200)

    @field_validator("time", "value", mode="before")
    @classmethod
    def empty_is_none(cls, value):
        # фронт присылает пустую строку, если поле не заполнено
        if value == "":
            return None
        return value
