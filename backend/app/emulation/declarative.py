"""Эмулятор, собранный из декларации конструктора, без отдельного класса на Python."""
from core import Device, Signal

from app.emulation.spec import DeviceTypeSpec


class DeclarativeDevice(Device):
    def __init__(self, spec: DeviceTypeSpec, serial: str = "0", client=None, logger=print):
        super().__init__(serial=serial, client=client, logger=logger)
        self.model = "custom_" + spec.family
        self.title = spec.title
        self._affects = {}
        self._events = []
        for item in spec.signals:
            self.add_signal(_to_signal(item))
            if item.affects is not None:
                self._affects[item.name] = item.affects
            if item.kind == "event":
                self._events.append(item.name)

    def on_command(self, name, value) -> None:
        # команда переводит связанное свойство в то же значение: закрыть клапан -> клапан закрыт
        target = self._affects.get(name)
        if target is not None:
            self.set_value(target, value)

    def tick(self, dt: int) -> None:
        # событие мгновенное: через тик сбрасывается
        for name in self._events:
            if self.signals[name].value != 0:
                self.set_value(name, 0)


def _to_signal(item) -> Signal:
    return Signal(
        name=item.name,
        title=item.title,
        control=item.control,
        management=item.management,
        kind=item.kind,
        value=item.default,
        measure=item.measure,
        minimum=item.min,
        maximum=item.max,
        layout=item.layout,
    )
