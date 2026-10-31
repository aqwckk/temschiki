"""Запущенные эмуляторы: общий цикл тиков, команды, физические входы, online/offline."""
import asyncio
import logging
import threading
from dataclasses import dataclass
from typing import Any, Callable, Optional

from app.emulation import registry
from app.emulation.errors import CommandRejected, DeviceNotRunning, DeviceOffline
from app.emulation.inputs import find_input

logger = logging.getLogger(__name__)

# слушатель получает (device_id, имя сигнала, новое значение)
Listener = Callable[[int, str, Any], None]


@dataclass
class Slot:
    family: str
    emulator: Any
    online: bool = True


class EmulatorRuntime:
    def __init__(self, interval: float = 1.0):
        self.interval = interval
        self._slots: dict[int, Slot] = {}
        self._listeners: list[Listener] = []
        self._lock = threading.RLock()
        self._task: Optional[asyncio.Task] = None

    def add(self, device_id: int, family: str) -> None:
        emulator = registry.create_emulator(family, serial=str(device_id))
        with self._lock:
            self._slots[device_id] = Slot(family=family, emulator=emulator)

    def remove(self, device_id: int) -> None:
        with self._lock:
            self._slots.pop(device_id, None)

    def is_running(self, device_id: int) -> bool:
        return device_id in self._slots

    def is_online(self, device_id: int) -> bool:
        slot = self._slots.get(device_id)
        if slot is None:
            return False
        return slot.online

    def set_online(self, device_id: int, online: bool) -> None:
        with self._lock:
            self._get_slot(device_id).online = online

    def values(self, device_id: int) -> dict[str, Any]:
        with self._lock:
            slot = self._get_slot(device_id)
            return _snapshot(slot)

    def command(self, device_id: int, signal: str, value: Any) -> None:
        with self._lock:
            slot = self._get_online_slot(device_id)
            _validate_command(slot, signal, value)
            payload = {"recv": [{"command": "management", "id": str(device_id), signal: value}]}
            changes = _collect_changes(slot, lambda: slot.emulator.handle_recv(payload))
        self._notify(device_id, changes)

    def simulate(self, device_id: int, input_name: str, value: Any) -> None:
        with self._lock:
            slot = self._get_online_slot(device_id)
            physical = find_input(slot.family, input_name)
            if physical is None:
                raise CommandRejected(f"у устройства нет физического входа {input_name}")
            changes = _collect_changes(slot, lambda: physical.apply(slot.emulator, value))
        self._notify(device_id, changes)

    def tick_all(self) -> None:
        all_changes = []
        with self._lock:
            for device_id, slot in self._slots.items():
                if not slot.online:
                    continue
                changes = _collect_changes(slot, lambda: slot.emulator.step(1))
                all_changes.append((device_id, changes))
        for device_id, changes in all_changes:
            self._notify(device_id, changes)

    def subscribe(self, listener: Listener) -> None:
        self._listeners.append(listener)

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(self.interval)
            try:
                self.tick_all()
            except Exception:
                logger.exception("ошибка в цикле тиков")

    def _get_slot(self, device_id: int) -> Slot:
        slot = self._slots.get(device_id)
        if slot is None:
            raise DeviceNotRunning(f"эмулятор устройства {device_id} не запущен")
        return slot

    def _get_online_slot(self, device_id: int) -> Slot:
        slot = self._get_slot(device_id)
        if not slot.online:
            raise DeviceOffline(f"устройство {device_id} недоступно")
        return slot

    def _notify(self, device_id: int, changes: dict[str, Any]) -> None:
        for name, value in changes.items():
            for listener in self._listeners:
                try:
                    listener(device_id, name, value)
                except Exception:
                    logger.exception("ошибка в слушателе сигналов")


def _snapshot(slot: Slot) -> dict[str, Any]:
    return {name: signal.value for name, signal in slot.emulator.signals.items()}


def _collect_changes(slot: Slot, action: Callable[[], None]) -> dict[str, Any]:
    before = _snapshot(slot)
    action()
    after = _snapshot(slot)
    changes = {}
    for name, value in after.items():
        if before.get(name) != value:
            changes[name] = value
    return changes


def _validate_command(slot: Slot, name: str, value: Any) -> None:
    signal = slot.emulator.signals.get(name)
    if signal is None:
        raise CommandRejected(f"у устройства нет сигнала {name}")
    if not signal.writable:
        raise CommandRejected(f"сигнал {name} только для чтения")
    if signal.minimum is not None and value < signal.minimum:
        raise CommandRejected(f"значение {name} меньше минимума {signal.minimum}")
    if signal.maximum is not None and value > signal.maximum:
        raise CommandRejected(f"значение {name} больше максимума {signal.maximum}")


runtime = EmulatorRuntime()
