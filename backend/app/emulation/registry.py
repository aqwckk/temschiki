"""Все типы устройств: готовые семейства из emulators/ и типы из конструктора."""
from typing import Optional

from devices import REGISTRY

from app.emulation import inputs
from app.emulation.declarative import DeclarativeDevice
from app.emulation.inputs import PhysicalInput
from app.emulation.spec import DeviceTypeSpec

_custom: dict[str, DeviceTypeSpec] = {}


def _silent(message: str) -> None:
    pass


def register_custom(spec: DeviceTypeSpec) -> None:
    _custom[spec.family] = spec


def unregister_custom(family: str) -> None:
    _custom.pop(family, None)


def custom_spec(family: str) -> Optional[DeviceTypeSpec]:
    return _custom.get(family)


def is_builtin(family: str) -> bool:
    return family in REGISTRY


def families() -> list[str]:
    return sorted(REGISTRY) + sorted(_custom)


def is_known(family: str) -> bool:
    return family in REGISTRY or family in _custom


def create_emulator(family: str, serial: str = "0"):
    if family in REGISTRY:
        device_class = REGISTRY[family]
        return device_class(serial=serial, client=None, logger=_silent)
    return DeclarativeDevice(_custom[family], serial=serial, logger=_silent)


def find_signal(family: str, name: str):
    emulator = create_emulator(family)
    return emulator.signals.get(name)


def inputs_for(family: str) -> list[PhysicalInput]:
    if family in REGISTRY:
        return inputs.inputs_for(family)
    # у типа из конструктора физическим входом считается любое свойство и событие
    result = []
    for item in _custom[family].signals:
        if not item.writable:
            result.append(PhysicalInput(item.name, item.title, "number", _setter(item.name)))
    return result


def find_input(family: str, name: str) -> Optional[PhysicalInput]:
    for item in inputs_for(family):
        if item.name == name:
            return item
    return None


def describe(family: str) -> dict:
    if family in REGISTRY:
        emulator = create_emulator(family)
        signals = [_normalize_signal(item) for item in emulator.declaration()]
    else:
        signals = [_describe_spec_signal(item) for item in _custom[family].signals]
    physical = [
        {"name": item.name, "title": item.title, "value_type": item.value_type}
        for item in inputs_for(family)
    ]
    return {
        "family": family,
        "title": create_emulator(family).title,
        "builtin": family in REGISTRY,
        "signals": signals,
        "inputs": physical,
    }


def _setter(name: str):
    def apply(emulator, value) -> None:
        emulator.set_value(name, emulator.clamp(name, value))

    return apply


def _normalize_signal(declaration: dict) -> dict:
    # ключи layout бывают числами, в JSON они все равно станут строками
    layout = declaration.get("layout")
    if layout:
        declaration["layout"] = {str(key): str(value) for key, value in layout.items()}
    return declaration


def _describe_spec_signal(item) -> dict:
    declaration = item.model_dump()
    declaration["management"] = item.management
    declaration["group"] = item.group
    return declaration
