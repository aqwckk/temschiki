"""Доступ к семействам эмуляторов из папки emulators/."""
from devices import REGISTRY

from app.emulation.inputs import inputs_for


def _silent(message: str) -> None:
    pass


def families() -> list[str]:
    return sorted(REGISTRY)


def is_known(family: str) -> bool:
    return family in REGISTRY


def create_emulator(family: str, serial: str = "0"):
    device_class = REGISTRY[family]
    return device_class(serial=serial, client=None, logger=_silent)


def _normalize_signal(declaration: dict) -> dict:
    # ключи layout бывают числами, в JSON они все равно станут строками
    layout = declaration.get("layout")
    if layout:
        declaration["layout"] = {str(key): str(value) for key, value in layout.items()}
    return declaration


def find_signal(family: str, name: str):
    emulator = create_emulator(family)
    return emulator.signals.get(name)


def describe(family: str) -> dict:
    emulator = create_emulator(family)
    signals = [_normalize_signal(item) for item in emulator.declaration()]
    physical = [
        {"name": item.name, "title": item.title, "value_type": item.value_type}
        for item in inputs_for(family)
    ]
    return {"family": family, "title": emulator.title, "signals": signals, "inputs": physical}
