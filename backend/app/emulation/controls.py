"""Главная команда устройства: что значит включить и выключить его одной кнопкой."""
from dataclasses import dataclass
from typing import Any, Optional

from app.emulation import registry
from app.emulation.runtime import runtime
from app.realtime import events


@dataclass(frozen=True)
class MainControl:
    on_signal: str
    on_value: Any
    off_signal: str
    off_value: Any
    state_signal: str
    off_state: Any = 0

    def is_on(self, values: dict) -> bool:
        return values.get(self.state_signal, self.off_state) != self.off_state


# у датчиков (протечка, дым, лифт) главной команды нет, кнопка включает и выключает питание
BUILTIN_CONTROLS = {
    "light": MainControl("lamp", 1, "lamp", 0, "lamp"),
    "counter": MainControl("load_relay", 1, "load_relay", 0, "load_relay"),
    "thermostat": MainControl("mode", 3, "mode", 0, "mode"),
    "ventilation": MainControl("mode", 1, "mode", 0, "mode"),
    "barrier": MainControl("open_cmd", 1, "close_cmd", 1, "state"),
}


def main_control(family: str) -> Optional[MainControl]:
    if family in BUILTIN_CONTROLS:
        return BUILTIN_CONTROLS[family]
    spec = registry.custom_spec(family)
    if spec is None:
        return None
    return _custom_control(spec)


def _custom_control(spec) -> Optional[MainControl]:
    # у типа из конструктора главная команда - первый переключатель, иначе первая команда
    commands = [signal for signal in spec.signals if signal.kind == "capability"]
    switches = [signal for signal in commands if signal.control == "switch"]
    candidates = switches or commands
    if not candidates:
        return None
    signal = candidates[0]
    state = signal.affects or signal.name
    return MainControl(signal.name, 1, signal.name, 0, state)


def is_on(device_id: int) -> bool:
    if not runtime.is_online(device_id):
        return False
    control = main_control(runtime.family(device_id))
    if control is None:
        return True
    return control.is_on(runtime.values(device_id))


def turn(device_id: int, on: bool) -> None:
    control = main_control(runtime.family(device_id))
    if control is None:
        runtime.set_online(device_id, on)
        events.publish_device_status(device_id, on)
        return
    if on:
        runtime.command(device_id, control.on_signal, control.on_value)
    else:
        runtime.command(device_id, control.off_signal, control.off_value)
