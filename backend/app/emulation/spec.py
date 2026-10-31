"""Декларативное описание типа устройства из конструктора."""
from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, model_validator

NAME_PATTERN = r"^[a-z][a-z0-9_]{0,31}$"
RESERVED_NAMES = ("fw",)

# property - измеряю, event - сообщаю о событии, capability - команда, setting - настройка
SignalKind = Literal["property", "event", "capability", "setting"]
Control = Literal["text", "switch", "range", "list", "graph", "counter", "button"]


class SignalSpec(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(pattern=NAME_PATTERN)
    title: str = Field(min_length=1, max_length=100)
    kind: SignalKind
    control: Control = "text"
    measure: str = Field(default="", max_length=20)
    min: Optional[float] = None
    max: Optional[float] = None
    default: Union[int, float] = 0
    layout: Optional[dict[str, str]] = None
    affects: Optional[str] = None

    @property
    def writable(self) -> bool:
        return self.kind in ("capability", "setting")

    @property
    def management(self) -> str:
        if self.writable:
            return "rw"
        return "r"

    @property
    def group(self) -> str:
        # те же три группы, что у готовых эмуляторов; событие показываем среди свойств
        if self.kind == "setting":
            return "setting"
        if self.kind == "capability":
            return "capability"
        return "property"

    @model_validator(mode="after")
    def check_values(self):
        if self.name in RESERVED_NAMES:
            raise ValueError(f"имя сигнала {self.name} зарезервировано")
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError(f"{self.name}: min больше max")
        if self.min is not None and self.default < self.min:
            raise ValueError(f"{self.name}: значение по умолчанию меньше min")
        if self.max is not None and self.default > self.max:
            raise ValueError(f"{self.name}: значение по умолчанию больше max")
        if self.affects is not None and not self.writable:
            raise ValueError(f"{self.name}: affects есть только у команд и настроек")
        return self


class DeviceTypeSpec(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    family: str = Field(pattern=NAME_PATTERN)
    title: str = Field(min_length=1, max_length=100)
    signals: list[SignalSpec] = Field(min_length=1)

    @model_validator(mode="after")
    def check_signals(self):
        names = [signal.name for signal in self.signals]
        if len(names) != len(set(names)):
            raise ValueError("имена сигналов должны быть уникальными")
        readable = {signal.name for signal in self.signals if not signal.writable}
        for signal in self.signals:
            if signal.affects is not None and signal.affects not in readable:
                raise ValueError(f"{signal.name}: affects должен указывать на свойство или событие")
        return self
