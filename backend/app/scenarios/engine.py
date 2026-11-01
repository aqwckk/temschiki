"""Исполнение сценариев: событие или ситуация, проверка условий, действия по порядку."""
import asyncio
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import TypeAdapter

from app.emulation import controls
from app.emulation.errors import CommandRejected, DeviceNotRunning, DeviceOffline
from app.emulation.runtime import EmulatorRuntime, runtime
from app.scenarios.blocks import ACTION_KINDS, Block, SituationCondition, compare
from app.services import emergencies, journal
from app.situations import catalog, evaluator
from app.situations.catalog import Situation

logger = logging.getLogger(__name__)

blocks_adapter = TypeAdapter(list[Block])
conditions_adapter = TypeAdapter(list[SituationCondition])

COMMAND_ATTEMPTS = 2
RETRY_DELAY = 1.0
WATCH_INTERVAL = 1.0


@dataclass
class LoadedScenario:
    id: int
    title: str
    blocks: list
    conditions: list

    def of_kind(self, *kinds: str) -> list:
        return [block for block in self.blocks if block.kind in kinds]


def load(scenario) -> LoadedScenario:
    return LoadedScenario(
        id=scenario.id,
        title=scenario.title,
        blocks=blocks_adapter.validate_python(scenario.blocks),
        conditions=conditions_adapter.validate_python(scenario.conditions or []),
    )


class ScenarioEngine:
    def __init__(self, emulators: EmulatorRuntime):
        self.emulators = emulators
        self._scenarios: list[LoadedScenario] = []
        self._last_values: dict[tuple[int, str], Any] = {}
        # состояние ситуаций по условиям сценариев, чтобы ловить момент начала
        self._situation_state: dict[tuple[int, str], bool] = {}
        self._fired_at: dict[tuple[int, str], str] = {}
        self._running: set[int] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._watch_task: Optional[asyncio.Task] = None
        self._lock = threading.Lock()
        self._subscribed = False

    def start(self, loop: asyncio.AbstractEventLoop, scenarios: list) -> None:
        self._loop = loop
        with self._lock:
            self._last_values.clear()
            self._situation_state.clear()
            self._fired_at.clear()
        self.reload(scenarios)
        if not self._subscribed:
            self.emulators.subscribe(self.on_signal)
            self._subscribed = True
        self._watch_task = loop.create_task(self._watch())

    async def stop(self) -> None:
        if self._watch_task is None:
            return
        self._watch_task.cancel()
        try:
            await self._watch_task
        except asyncio.CancelledError:
            pass
        self._watch_task = None

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

    def check_situations(self, now: Optional[datetime] = None) -> None:
        """Сравнивает ситуации с прошлой проверкой и запускает сценарии, где ситуация началась."""
        if now is None:
            now = datetime.now()
        states = self.emulators.all_states()
        manual = emergencies.board.active_types()
        with self._lock:
            scenarios = list(self._scenarios)
        for scenario in scenarios:
            for condition in scenario.conditions:
                situation = catalog.find(condition.type)
                if situation is None:
                    continue
                active = evaluator.is_active(situation, condition.value, manual, states, now)
                if self._should_fire(scenario.id, condition, active, now):
                    self._schedule(
                        scenario,
                        _cause(situation, condition),
                        check_conditions=True,
                        situation=situation,
                        condition=condition,
                    )

    def _should_fire(self, scenario_id: int, condition: SituationCondition, active: bool, now: datetime) -> bool:
        key = (scenario_id, condition.id)
        with self._lock:
            was_active = self._situation_state.get(key, False)
            self._situation_state[key] = active
            if condition.time is None:
                return active and not was_active
            # со временем: срабатывает в указанную минуту, если ситуация идет, раз в сутки
            if not active or now.strftime("%H:%M") != condition.time:
                return False
            stamp = now.strftime("%Y-%m-%d %H:%M")
            if self._fired_at.get(key) == stamp:
                return False
            self._fired_at[key] = stamp
            return True

    async def _watch(self) -> None:
        while True:
            await asyncio.sleep(WATCH_INTERVAL)
            try:
                emergencies.expire_due()
                self.check_situations()
            except Exception:
                logger.exception("ошибка при проверке ситуаций")

    def _schedule(
        self,
        scenario: LoadedScenario,
        cause: str,
        check_conditions: bool,
        situation: Optional[Situation] = None,
        condition: Optional[SituationCondition] = None,
    ) -> None:
        if self._loop is None or self._loop.is_closed():
            logger.warning("движок не запущен, сценарий %s пропущен", scenario.id)
            return
        coroutine = self._execute(scenario, cause, check_conditions, situation, condition)
        asyncio.run_coroutine_threadsafe(coroutine, self._loop)

    async def _execute(
        self,
        scenario: LoadedScenario,
        cause: str,
        check_conditions: bool,
        situation: Optional[Situation],
        condition: Optional[SituationCondition],
    ) -> None:
        # один и тот же сценарий не запускается повторно, пока идет
        if scenario.id in self._running:
            return
        self._running.add(scenario.id)
        try:
            await self._run_blocks(scenario, cause, check_conditions, situation, condition)
        except Exception:
            logger.exception("сценарий %s упал", scenario.id)
        finally:
            self._running.discard(scenario.id)

    async def _run_blocks(
        self,
        scenario: LoadedScenario,
        cause: str,
        check_conditions: bool,
        situation: Optional[Situation],
        condition: Optional[SituationCondition] = None,
    ) -> None:
        started_at = datetime.now(timezone.utc)
        if check_conditions:
            failed = self._failed_condition(scenario)
            if failed is not None:
                journal.save_run(scenario.id, cause, "skipped", failed, [], started_at)
                return

        blocks = scenario.of_kind(*ACTION_KINDS)
        device_on = None
        if condition is not None:
            blocks, device_on = _reaction_plan(blocks, condition)

        steps = []
        for group in _parallel_groups(blocks):
            # шаг сценария: блоки одного столбца выполняются одновременно
            results = await asyncio.gather(*(self._do_action(scenario, block, device_on) for block in group))
            for block, error in zip(group, results):
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

    async def _do_action(self, scenario: LoadedScenario, block, device_on: Optional[bool] = None) -> str:
        if block.kind == "device":
            on = block.on
            if device_on is not None:
                on = device_on
            return await self._with_retry(lambda: controls.turn(block.device_id, on))
        if block.kind == "command":
            return await self._with_retry(lambda: self.emulators.command(block.device_id, block.signal, block.value))
        if block.kind == "delay":
            await asyncio.sleep(block.seconds)
            return ""
        return f"неизвестное действие {block.kind}"

    async def _with_retry(self, action) -> str:
        error = ""
        for attempt in range(COMMAND_ATTEMPTS):
            try:
                action()
                return ""
            except DeviceOffline as exc:
                # устройство может вернуться, пробуем еще раз
                error = str(exc)
                await asyncio.sleep(RETRY_DELAY)
            except (DeviceNotRunning, CommandRejected) as exc:
                error = str(exc)
                break
        return error


def _cause(situation: Situation, condition: SituationCondition) -> str:
    text = f"ситуация: {situation.label}"
    if situation.unit and condition.value is not None:
        text += f" {condition.value:g}{situation.unit}"
    if condition.time:
        text += f" в {condition.time}"
    return text


def _reaction_plan(blocks: list, condition: SituationCondition) -> tuple[list, Optional[bool]]:
    """Что делать с устройствами по реакции условия: включить, выключить или не трогать.

    Остальные реакции (уведомление, поддержка, свое действие) обрабатывает фронт.
    """
    if condition.action == "on":
        return blocks, True
    if condition.action == "off":
        return blocks, False
    return [block for block in blocks if block.kind != "device"], None


def _parallel_groups(blocks: list) -> list[list]:
    groups = []
    for block in blocks:
        col = getattr(block, "col", None)
        if col is not None and groups and getattr(groups[-1][0], "col", None) == col:
            groups[-1].append(block)
        else:
            groups.append([block])
    return groups


def _fired_trigger(scenario: LoadedScenario, device_id: int, name: str, old: Any, new: Any):
    # срабатывает только на переходе: раньше условие не выполнялось, теперь выполняется
    for trigger in scenario.of_kind("trigger"):
        if trigger.device_id != device_id or trigger.signal != name:
            continue
        if compare(new, trigger.op, trigger.value) and not compare(old, trigger.op, trigger.value):
            return trigger
    return None


engine = ScenarioEngine(runtime)
