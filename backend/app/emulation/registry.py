"""Доступ к семействам эмуляторов из папки emulators/."""
import sys

from app.config import settings

# модули эмуляторов импортируют друг друга как top-level (from core import ...)
_emulators_path = str(settings.emulators_dir)
if _emulators_path not in sys.path:
    sys.path.insert(0, _emulators_path)

from devices import REGISTRY  # noqa: E402


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


def describe(family: str) -> dict:
    emulator = create_emulator(family)
    signals = [_normalize_signal(item) for item in emulator.declaration()]
    return {"family": family, "title": emulator.title, "signals": signals}
