from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.emulation import registry
from app.models import Device, Scenario, ScenarioRun
from app.scenarios.engine import engine
from app.scenarios.errors import ScenarioInvalid
from app.schemas import ScenarioIn
from app.situations import catalog


def list_scenarios(session: Session) -> list[Scenario]:
    return list(session.scalars(select(Scenario).order_by(Scenario.position, Scenario.id)))


def get_scenario(session: Session, scenario_id: int) -> Optional[Scenario]:
    return session.get(Scenario, scenario_id)


def create_scenario(session: Session, data: ScenarioIn) -> Scenario:
    validate_references(session, data)
    last_position = session.scalar(select(func.max(Scenario.position)))
    if last_position is None:
        last_position = -1
    scenario = Scenario(
        title=data.title,
        enabled=data.enabled,
        position=last_position + 1,
        blocks=_dump(data.blocks),
        conditions=_dump(data.conditions),
    )
    session.add(scenario)
    session.commit()
    _reload(session)
    return scenario


def update_scenario(session: Session, scenario: Scenario, data: ScenarioIn) -> Scenario:
    validate_references(session, data)
    scenario.title = data.title
    scenario.enabled = data.enabled
    scenario.blocks = _dump(data.blocks)
    scenario.conditions = _dump(data.conditions)
    session.commit()
    _reload(session)
    return scenario


def reorder(session: Session, ids: list[int]) -> list[Scenario]:
    by_id = {scenario.id: scenario for scenario in list_scenarios(session)}
    if set(ids) != set(by_id):
        raise ScenarioInvalid("в новом порядке должны быть все сценарии ровно по одному разу")
    for position, scenario_id in enumerate(ids):
        by_id[scenario_id].position = position
    session.commit()
    return list_scenarios(session)


def delete_scenario(session: Session, scenario: Scenario) -> None:
    session.execute(delete(ScenarioRun).where(ScenarioRun.scenario_id == scenario.id))
    session.delete(scenario)
    session.commit()
    _reload(session)


def remove_device(session: Session, device_id: int) -> None:
    """Убирает удаленное устройство из всех сценариев, как это делает фронт."""
    for scenario in list_scenarios(session):
        kept = [block for block in scenario.blocks if block.get("device_id") != device_id]
        if len(kept) != len(scenario.blocks):
            scenario.blocks = kept
    session.commit()
    _reload(session)


def validate_references(session: Session, data: ScenarioIn) -> None:
    """Проверяет устройства и сигналы в блоках и ситуации в условиях."""
    for block in data.blocks:
        if not hasattr(block, "device_id"):
            continue
        device = session.get(Device, block.device_id)
        if device is None:
            raise ScenarioInvalid(f"блок {block.id}: устройство {block.device_id} не найдено")
        if block.kind == "device":
            continue
        signal = registry.find_signal(device.family, block.signal)
        if signal is None:
            raise ScenarioInvalid(f"блок {block.id}: у устройства {device.name} нет сигнала {block.signal}")
        if block.kind == "command" and not signal.writable:
            raise ScenarioInvalid(f"блок {block.id}: сигналом {block.signal} нельзя управлять")
    for condition in data.conditions:
        if catalog.find(condition.type) is None:
            raise ScenarioInvalid(f"неизвестная ситуация {condition.type}")


def _reload(session: Session) -> None:
    engine.reload(list_scenarios(session))


def _dump(items: list) -> list[dict]:
    return [item.model_dump(mode="json") for item in items]
