"""Показания устройства человеческими строками для карточки: "Температура: 21.5 °C"."""
from typing import Any

from app.emulation import registry

MAX_PARAMS = 3


def params(family: str, values: dict[str, Any]) -> list[str]:
    result = []
    for signal in registry.describe(family)["signals"]:
        # служебные сигналы (прошивка) и мгновенные события на карточке не нужны
        if signal["group"] != "property" or signal["kind"] in ("event", "system"):
            continue
        if signal["name"] not in values:
            continue
        result.append(f"{signal['title']}: {_format(signal, values[signal['name']])}")
        if len(result) == MAX_PARAMS:
            break
    return result


def _format(signal: dict, value: Any) -> str:
    layout = signal.get("layout") or {}
    label = layout.get(_layout_key(value))
    if label is not None:
        return label
    text = _number(value)
    measure = signal.get("measure")
    if measure:
        return f"{text} {measure}"
    return text


def _layout_key(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _number(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.1f}".rstrip("0").rstrip(".")
    return str(value)
