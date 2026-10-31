"""Зеркало на платформу Ujin: наши устройства публикуют сигналы в устройства стенда."""
import asyncio
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Optional

from app.config import settings
from app.emulation import registry
from app.ujin import credentials as credentials_module
from app.ujin.credentials import UjinCredentials, UjinDevice

# клиент лежит в emulators/, путь к ним добавляет app.emulation
from ujin_client import UjinClient

logger = logging.getLogger(__name__)


class QuietUjinClient(UjinClient):
    """Клиент эмуляторов печатает журнал каждого вызова в stdout, у нас он идет в лог."""

    def _journal(self, call: str, path: str, rows: list) -> None:
        logger.debug("ujin %s %s %s", call, path, rows)


@dataclass
class Binding:
    device_id: int
    family: str
    target: UjinDevice
    announced: bool = False
    pending: dict[str, Any] = field(default_factory=dict)


class UjinMirror:
    def __init__(self):
        self.mode = settings.ujin_mode
        self.credentials: Optional[UjinCredentials] = None
        self.client: Optional[UjinClient] = None
        self._bindings: dict[int, Binding] = {}
        self._lock = threading.Lock()
        self._task: Optional[asyncio.Task] = None
        self.published = 0
        self.last_flush_at: Optional[datetime] = None
        self.last_error = ""

    @property
    def enabled(self) -> bool:
        return self.credentials is not None

    def load_credentials(self) -> None:
        self.credentials = credentials_module.load(settings.ujin_credentials_file)
        if self.credentials is None:
            logger.warning("файл доступов Ujin не найден, зеркало выключено")
            return
        self.client = QuietUjinClient(
            settings.ujin_base_url,
            device_token="",
            dry_run=self.mode == "dry",
            logger=logger.debug,
            cls="integrations_devices",
            signal_prefix="integrations_devices_",
            ust=self.credentials.ust,
            apartment_id=self.credentials.apartment_id,
        )

    def bind(self, device_id: int, family: str, values: dict[str, Any]) -> None:
        """Привязывает устройство к устройству стенда того же семейства, если оно свободно."""
        if not self.enabled:
            return
        target = self.credentials.device_for(family)
        if target is None:
            return
        with self._lock:
            if any(binding.target.ext == target.ext for binding in self._bindings.values()):
                return
            binding = Binding(device_id=device_id, family=family, target=target)
            binding.pending.update(_publishable(family, values))
            self._bindings[device_id] = binding

    def unbind(self, device_id: int) -> None:
        with self._lock:
            self._bindings.pop(device_id, None)

    def on_signal(self, device_id: int, name: str, value: Any) -> None:
        with self._lock:
            binding = self._bindings.get(device_id)
            if binding is None:
                return
            binding.pending.update(_publishable(binding.family, {name: value}))

    def status(self) -> dict:
        with self._lock:
            bindings = [
                {
                    "device_id": binding.device_id,
                    "family": binding.family,
                    "ext": binding.target.ext,
                    "serialnumber": binding.target.serialnumber,
                }
                for binding in self._bindings.values()
            ]
        return {
            "mode": self.mode,
            "enabled": self.enabled,
            "bindings": bindings,
            "published": self.published,
            "last_flush_at": self.last_flush_at,
            "last_error": self.last_error,
        }

    async def start(self) -> None:
        if self.enabled and self._task is None:
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
            await asyncio.sleep(settings.ujin_flush_interval)
            # запросы к стенду блокирующие, уводим их из цикла сервера
            await asyncio.to_thread(self.flush)

    def flush(self) -> None:
        with self._lock:
            work = []
            for binding in self._bindings.values():
                if binding.pending:
                    work.append((binding, dict(binding.pending)))
                    binding.pending.clear()
        for binding, rows in work:
            self._publish(binding, rows)
        self.last_flush_at = datetime.now(timezone.utc)

    def _publish(self, binding: Binding, rows: dict[str, Any]) -> None:
        target = binding.target
        try:
            if not binding.announced:
                self._announce(binding)
            batch = [{"signal": name, "value": value} for name, value in rows.items()]
            response = self.client.update_signals(target.ext, target.model, batch)
            if response.get("error"):
                self.last_error = f"{target.ext}: {response.get('message')}"
                return
            self.published += len(batch)
        except Exception as exc:
            self.last_error = f"{target.ext}: {exc}"
            logger.warning("публикация в Ujin не удалась: %s", exc)

    def _announce(self, binding: Binding) -> None:
        # новый сигнал на стенде сначала создается коротким именем, иначе значение теряется
        target = binding.target
        names = _publishable_names(binding.family)
        rows = [{"sn": target.ext, "s": name, "v": 0.001, "c": target.publish_class} for name in names]
        self.client.publish_group([], new_short=rows)
        binding.announced = True


@lru_cache
def _publishable_names(family: str) -> tuple[str, ...]:
    emulator = registry.create_emulator(family)
    return tuple(name for name, signal in emulator.signals.items() if signal.publishable and name != "fw")


def _publishable(family: str, values: dict[str, Any]) -> dict[str, Any]:
    names = _publishable_names(family)
    result = {}
    for name, value in values.items():
        if name not in names:
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        # стенд не пишет 0, вместо него 0.001
        if value == 0:
            value = 0.001
        result[name] = value
    return result


mirror = UjinMirror()
