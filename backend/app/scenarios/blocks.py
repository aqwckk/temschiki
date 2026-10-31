"""Блоки сценария. Порядок блоков задает пользователь перетаскиванием."""
import operator
from typing import Annotated, Any, Literal, Union
from uuid import uuid4

from pydantic import BaseModel, Field

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


Block = Annotated[
    Union[TriggerBlock, ConditionBlock, CommandBlock, NotifyBlock, DelayBlock],
    Field(discriminator="kind"),
]

ACTION_KINDS = ("command", "notify", "delay")
