"""Исполнение сценариев: событие, проверка условий, действия по порядку."""
import asyncio
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import TypeAdapter

from app.emulation.errors import CommandRejected, DeviceNotRunning, DeviceOffline
from app.emulation.runtime import EmulatorRuntime, runtime
from app.scenarios.blocks import ACTION_KINDS, Block, compare
from app.services import journal

logger = logging.getLogger(__name__)

blocks_adapter = TypeAdapter(list[Block])

COMMAND_ATTEMPTS = 2
RETRY_DELAY = 1.0


@dataclass
class LoadedScenario:
    id: int
    title: str
    blocks: list

    def of_kind(self, *kinds: str) -> list:
        return [block for block in self.blocks if block.kind in kinds]


def load(scenario) -> LoadedScenario:
    blocks = blocks_adapter.validate_python(scenario.blocks)
    return LoadedScenario(id=scenario.id, title=scenario.title, blocks=blocks)


class ScenarioEngine:
    def __init__(self, emulators: EmulatorRuntime):
        self.emulators = emulators
        self._scenarios: list[LoadedScenario] = []
        self._last_values: dict[tuple[int, str], Any] = {}
        self._running: set[int] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock = threading.Lock()
        self._subscribed = False

    def start(self, loop: asyncio.AbstractEventLoop, scenarios: list) -> None:
        self._loop = loop
        with self._lock:
            self._last_values.clear()
        self.reload(scenarios)
        if not self._subscribed:
            self.emulators.subscribe(self.on_signal)
            self._subscribed = True

    def reload(self, scenarios: list) -> None:
        loaded = [load(scenario) for scenario in scenarios if scenario.enabled]
        with self._lock:
            self._scenarios = loaded

    def forget_device(self, device_id: int) -> None:
        # id удаленного устройства может достаться новому
        with self._lock:
            for key in [key for key in self._last_values if key[0] == device_id]:
                del self._last_values[key]

    def run_now(self, scenario) -> None:
        self._schedule(load(scenario), "ручной запуск", check_conditions=False)

    def on_signal(self, device_id: int, name: str, value: Any) -> None:
        with self._lock:
            old = self._last_values.get((device_id, name))
            self._last_values[(device_id, name)] = value
            scenarios = list(self._scenarios)
        for scenario in scenarios:
            trigger = _fired_trigger(scenario, device_id, name, old, value)
            if trigger is not None:
                cause = f"устройство {device_id}: {name} {trigger.op} {trigger.value}"
                self._schedule(scenario, cause, check_conditions=True)

    def _schedule(self, scenario: LoadedScenario, cause: str, check_conditions: bool) -> None:
        if self._loop is None or self._loop.is_closed():
            logger.warning("движок не запущен, сценарий %s пропущен", scenario.id)
            return
        coroutine = self._execute(scenario, cause, check_conditions)
        asyncio.run_coroutine_threadsafe(coroutine, self._loop)

    async def _execute(self, scenario: LoadedScenario, cause: str, check_conditions: bool) -> None:
        # один и тот же сценарий не запускается повторно, пока идет
        if scenario.id in self._running:
            return
        self._running.add(scenario.id)
        try:
            await self._run_blocks(scenario, cause, check_conditions)
        except Exception:
            logger.exception("сценарий %s упал", scenario.id)
        finally:
            self._running.discard(scenario.id)

    async def _run_blocks(self, scenario: LoadedScenario, cause: str, check_conditions: bool) -> None:
        started_at = datetime.now(timezone.utc)
        if check_conditions:
            failed = self._failed_condition(scenario)
            if failed is not None:
                journal.save_run(scenario.id, cause, "skipped", failed, [], started_at)
                return

        steps = []
        for block in scenario.of_kind(*ACTION_KINDS):
            error = await self._do_action(scenario, block)
            steps.append({"block_id": block.id, "kind": block.kind, "ok": error == "", "error": error})

        errors = [step["error"] for step in steps if step["error"]]
        if errors:
            journal.save_run(scenario.id, cause, "failed", errors[0], steps, started_at)
        else:
            journal.save_run(scenario.id, cause, "success", "", steps, started_at)

    def _failed_condition(self, scenario: LoadedScenario) -> Optional[str]:
        for block in scenario.of_kind("condition"):
            if not self.emulators.is_online(block.device_id):
                return f"устройство {block.device_id} недоступно"
            current = self.emulators.values(block.device_id).get(block.signal)
            if not compare(current, block.op, block.value):
                return f"условие не выполнено: {block.signal} = {current}"
        return None

    async def _do_action(self, scenario: LoadedScenario, block) -> str:
        if block.kind == "command":
            return await self._send_command(scenario, block)
        if block.kind == "notify":
            journal.add_notification(block.target, block.message, scenario.id)
            return ""
        if block.kind == "delay":
            await asyncio.sleep(block.seconds)
            return ""
        return f"неизвестное действие {block.kind}"

    async def _send_command(self, scenario: LoadedScenario, block) -> str:
        error = ""
        for attempt in range(COMMAND_ATTEMPTS):
            try:
                self.emulators.command(block.device_id, block.signal, block.value)
                return ""
            except DeviceOffline as exc:
                # устройство может вернуться, пробуем еще раз
                error = str(exc)
                await asyncio.sleep(RETRY_DELAY)
            except (DeviceNotRunning, CommandRejected) as exc:
                error = str(exc)
                break
        journal.add_notification("concierge", f"Сценарий «{scenario.title}»: {error}", scenario.id)
        return error


def _fired_trigger(scenario: LoadedScenario, device_id: int, name: str, old: Any, new: Any):
    # срабатывает только на переходе: раньше условие не выполнялось, теперь выполняется
    for trigger in scenario.of_kind("trigger"):
        if trigger.device_id != device_id or trigger.signal != name:
            continue
        if compare(new, trigger.op, trigger.value) and not compare(old, trigger.op, trigger.value):
            return trigger
    return None


engine = ScenarioEngine(runtime)
