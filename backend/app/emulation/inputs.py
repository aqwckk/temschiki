"""Физические входы эмуляторов: то, что в жизни делает среда, а не пользователь."""
from dataclasses import dataclass
from typing import Callable, Optional


@dataclass(frozen=True)
class PhysicalInput:
    name: str
    title: str
    value_type: str
    apply: Callable


def _leak_wet(emulator, value) -> None:
    emulator.set_wet(bool(value))


def _barrier_obstacle(emulator, value) -> None:
    emulator.set_obstacle(bool(value))


def _fire_smoke(emulator, value) -> None:
    emulator.set_smoke(int(value))


def _thermostat_fault(emulator, value) -> None:
    emulator.set_fault(bool(value))


def _ventilation_co2(emulator, value) -> None:
    emulator.set_value("co2", float(value))


INPUTS = {
    "leak": [PhysicalInput("wet", "Намочить датчик", "bool", _leak_wet)],
    "barrier": [PhysicalInput("obstacle", "Препятствие под стрелой", "bool", _barrier_obstacle)],
    "fire": [PhysicalInput("smoke", "Уровень дыма, %", "number", _fire_smoke)],
    "thermostat": [PhysicalInput("fault", "Отказ датчика", "bool", _thermostat_fault)],
    "ventilation": [PhysicalInput("co2", "CO2 в помещении, ppm", "number", _ventilation_co2)],
}


def inputs_for(family: str) -> list[PhysicalInput]:
    return INPUTS.get(family, [])


def find_input(family: str, name: str) -> Optional[PhysicalInput]:
    for item in inputs_for(family):
        if item.name == name:
            return item
    return None
