"""Зеркало на платформу Ujin.

Вверх: наши устройства публикуют сигналы в устройства стенда от имени сотрудника УК.
Вниз: команды из кабинета применяются к эмуляторам. Сигналы integrations_devices_*
через get-device-info не видны (автословари скрыты), доставку подтверждает только
панель сигналов, поэтому чтение используется для команд, а не для проверки.
"""
import asyncio
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Optional

from app.config import settings
from app.emulation import registry
from app.emulation.runtime import runtime
from app.ujin import auth
from app.ujin import credentials as credentials_module
from app.ujin.credentials import UjinCredentials, UjinDevice

# клиент лежит в emulators/, путь к ним добавляет app.emulation
from ujin_client import UjinClient

logger = logging.getLogger(__name__)

PUBLISH_CLASS = "integrations_devices"


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
    remote: dict[str, Any] = field(default_factory=dict)
    seen_tasks: dict[str, str] = field(default_factory=dict)


class UjinMirror:
    def __init__(self):
        self.mode = settings.ujin_mode
        self.credentials: Optional[UjinCredentials] = None
        self._token = ""
        self._bindings: dict[int, Binding] = {}
        self._lock = threading.Lock()
        self._task: Optional[asyncio.Task] = None
        self.published = 0
        self.last_flush_at: Optional[datetime] = None
        self.last_readback_at: Optional[datetime] = None
        self.last_error = ""
        self.auth_message = ""
        self.commands_applied = 0
        self.last_command = ""

    @property
    def enabled(self) -> bool:
        return self.credentials is not None

    @property
    def live(self) -> bool:
        return self.mode == "live"

    def load_credentials(self) -> None:
        self.credentials = credentials_module.load(settings.ujin_credentials_file)
        if self.credentials is None:
            logger.warning("файл доступов Ujin не найден, зеркало выключено")

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
            bindings = [_binding_status(binding) for binding in self._bindings.values()]
        return {
            "mode": self.mode,
            "enabled": self.enabled,
            "auth": self.auth_message,
            "bindings": bindings,
            "published": self.published,
            "last_flush_at": self.last_flush_at,
            "last_readback_at": self.last_readback_at,
            "commands_applied": self.commands_applied,
            "last_command": self.last_command,
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
                work.append((binding, dict(binding.pending)))
                binding.pending.clear()
        for binding, rows in work:
            if rows:
                self._publish(binding, rows)
            if self.live:
                self._read_back(binding)
        self.last_flush_at = datetime.now(timezone.utc)

    def _token_for_requests(self) -> str:
        """ust сотрудника УК, если он есть в доступах, иначе ust резидента."""
        if not self.live or self.credentials.employee is None:
            return self.credentials.ust
        if not self._token:
            try:
                self._token = auth.login(settings.ujin_base_url, self.credentials.employee)
                self.auth_message = "вход сотрудника выполнен"
            except Exception as exc:
                self.auth_message = f"вход сотрудника не удался: {exc}"
                return self.credentials.ust
        return self._token

    def _client(self, target: UjinDevice) -> UjinClient:
        return QuietUjinClient(
            settings.ujin_base_url,
            device_token="",
            dry_run=not self.live,
            logger=logger.debug,
            cls=PUBLISH_CLASS,
            signal_prefix=PUBLISH_CLASS + "_",
            ust=self._token_for_requests(),
            apartment_id=target.apartment_id,
        )

    def _publish(self, binding: Binding, rows: dict[str, Any]) -> None:
        target = binding.target
        try:
            client = self._client(target)
            if not binding.announced:
                self._announce(client, binding)
            batch = [{"signal": name, "value": value} for name, value in rows.items()]
            response = client.update_signals(target.ext, target.model, batch)
            if response.get("error"):
                self._fail(f"{target.ext}: {response.get('message')}")
                return
            self.published += len(batch)
        except Exception as exc:
            self._fail(f"{target.ext}: {exc}")

    def _announce(self, client: UjinClient, binding: Binding) -> None:
        # новый сигнал на стенде сначала создается коротким именем, иначе значение теряется
        target = binding.target
        names = _publishable_names(binding.family)
        rows = [{"sn": target.ext, "s": name, "v": 0.001, "c": target.publish_class} for name in names]
        client.publish_group([], new_short=rows)
        binding.announced = True

    def _read_back(self, binding: Binding) -> None:
        """Читает устройство со стенда и забирает команды из кабинета."""
        target = binding.target
        try:
            info = self._client(target).get_device_info(self._token_for_requests(), target.serialnumber)
        except Exception as exc:
            self._fail(f"чтение {target.ext}: {exc}")
            return
        if not isinstance(info, dict) or info.get("error"):
            self._fail(f"чтение {target.ext}: {info.get('message')}")
            return
        binding.remote = _remote_values(info)
        self.last_readback_at = datetime.now(timezone.utc)
        self._apply_tasks(binding, info)

    def _apply_tasks(self, binding: Binding, info: dict) -> None:
        for name, value in UjinClient.pending_tasks(info).items():
            key = _task_key(info, name) or f"{name}={value}"
            # одна и та же команда исполняется один раз
            if binding.seen_tasks.get(name) == key:
                continue
            binding.seen_tasks[name] = key
            short = _short_name(name)
            try:
                runtime.command(binding.device_id, short, _number(value))
                self.commands_applied += 1
                self.last_command = f"{binding.target.ext}: {short} = {value}"
            except Exception as exc:
                self.last_command = f"{binding.target.ext}: {short} не выполнена ({exc})"

    def _fail(self, message: str) -> None:
        self.last_error = message
        logger.warning("Ujin: %s", message)
        # возможно, истек токен сотрудника: в следующий раз войдем заново
        self._token = ""


def _binding_status(binding: Binding) -> dict:
    return {
        "device_id": binding.device_id,
        "family": binding.family,
        "ext": binding.target.ext,
        "serialnumber": binding.target.serialnumber,
        "remote": dict(binding.remote),
    }


def _short_name(name: str) -> str:
    prefix = PUBLISH_CLASS + "_"
    if name.startswith(prefix):
        return name[len(prefix):]
    return name


def _remote_values(info: dict) -> dict[str, Any]:
    result = {}
    for signal in (info.get("data") or {}).get("signals") or []:
        name = str(signal.get("name") or signal.get("signal_name") or "")
        value = (signal.get("state") or {}).get("value", signal.get("value"))
        if name and value not in (None, ""):
            result[_short_name(name)] = value
    return result


def _task_key(info: dict, name: str) -> str:
    for signal in (info.get("data") or {}).get("signals") or []:
        if (signal.get("name") or signal.get("signal_name")) == name:
            return str(signal.get("signal_task_dt") or signal.get("task_dt") or "")
    return ""


def _number(value: Any) -> Any:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value
    if number.is_integer():
        return int(number)
    return number


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
