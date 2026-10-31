from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.emulation import registry
from app.models import Device, Scenario, ScenarioRun
from app.scenarios.engine import engine
from app.scenarios.errors import ScenarioInvalid
from app.schemas import ScenarioIn


def list_scenarios(session: Session) -> list[Scenario]:
    return list(session.scalars(select(Scenario).order_by(Scenario.id)))


def get_scenario(session: Session, scenario_id: int) -> Optional[Scenario]:
    return session.get(Scenario, scenario_id)


def create_scenario(session: Session, data: ScenarioIn) -> Scenario:
    validate_references(session, data)
    scenario = Scenario(title=data.title, enabled=data.enabled, blocks=_dump_blocks(data))
    session.add(scenario)
    session.commit()
    engine.reload(list_scenarios(session))
    return scenario


def update_scenario(session: Session, scenario: Scenario, data: ScenarioIn) -> Scenario:
    validate_references(session, data)
    scenario.title = data.title
    scenario.enabled = data.enabled
    scenario.blocks = _dump_blocks(data)
    session.commit()
    engine.reload(list_scenarios(session))
    return scenario


def delete_scenario(session: Session, scenario: Scenario) -> None:
    session.execute(delete(ScenarioRun).where(ScenarioRun.scenario_id == scenario.id))
    session.delete(scenario)
    session.commit()
    engine.reload(list_scenarios(session))


def validate_references(session: Session, data: ScenarioIn) -> None:
    """Проверяет, что устройства существуют, а сигналы есть у их семейства."""
    for block in data.blocks:
        if not hasattr(block, "device_id"):
            continue
        device = session.get(Device, block.device_id)
        if device is None:
            raise ScenarioInvalid(f"блок {block.id}: устройство {block.device_id} не найдено")
        signal = registry.find_signal(device.family, block.signal)
        if signal is None:
            raise ScenarioInvalid(f"блок {block.id}: у устройства {device.name} нет сигнала {block.signal}")
        if block.kind == "command" and not signal.writable:
            raise ScenarioInvalid(f"блок {block.id}: сигналом {block.signal} нельзя управлять")


def _dump_blocks(data: ScenarioIn) -> list[dict]:
    return [block.model_dump(mode="json") for block in data.blocks]
