"""Ситуации - события на языке жителя. Каждая знает, по каким датчикам ее узнать."""
from dataclasses import dataclass
from typing import Any, Optional


@dataclass(frozen=True)
class SensorRule:
    family: str
    signal: str
    op: str
    # None - порог берется из условия сценария
    value: Any = None


@dataclass(frozen=True)
class Emulation:
    """Как изобразить ситуацию на эмуляторах, когда житель запускает ее вручную."""

    family: str
    input: str
    on_value: Any
    off_value: Any


@dataclass(frozen=True)
class Situation:
    type: str
    label: str
    unit: Optional[str] = None
    value: Optional[float] = None
    no_time: bool = False
    alarm: bool = False
    night: bool = False
    custom: bool = False
    sensors: tuple = ()
    emulations: tuple = ()


BUILTIN = (
    Situation("water", "Отключили воду"),
    Situation("power", "Нет электричества"),
    Situation("gas", "Отключили газ"),
    Situation("internet", "Нет интернета"),
    Situation("heating", "Отключили отопление"),
    Situation("door", "Открыта дверь", sensors=(SensorRule("barrier", "state", "!=", 0),)),
    Situation("away", "Никого нет дома"),
    Situation(
        "leak",
        "Протечка",
        no_time=True,
        alarm=True,
        sensors=(SensorRule("leak", "leak", "==", 1), SensorRule("hub", "leak", "==", 1)),
        emulations=(Emulation("leak", "wet", 1, 0),),
    ),
    Situation(
        "smoke",
        "Дым в помещении",
        no_time=True,
        alarm=True,
        sensors=(SensorRule("fire", "alarm", "==", 1),),
        emulations=(Emulation("fire", "smoke", 100, 0),),
    ),
    Situation("night", "Наступила ночь", no_time=True, night=True),
    Situation("cold", "Температура ниже", unit="°C", value=18,
              sensors=(SensorRule("thermostat", "temperature", "<"),)),
    Situation("hot", "Температура выше", unit="°C", value=28,
              sensors=(SensorRule("thermostat", "temperature", ">"),)),
)

_custom: dict[str, Situation] = {}


def register_custom(type_: str, label: str) -> Situation:
    situation = Situation(type_, label, custom=True)
    _custom[type_] = situation
    return situation


def all_situations() -> list[Situation]:
    return list(BUILTIN) + list(_custom.values())


def find(type_: str) -> Optional[Situation]:
    for situation in all_situations():
        if situation.type == type_:
            return situation
    return None


def find_by_label(label: str) -> Optional[Situation]:
    for situation in all_situations():
        if situation.label.lower() == label.lower():
            return situation
    return None
