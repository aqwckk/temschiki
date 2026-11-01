"""Демо-квартира из кейса: создается при первом запуске, если база пустая."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.emulation import registry
from app.emulation.spec import DeviceTypeSpec
from app.models import Device, Scenario
from app.schemas import DeviceCreate, ScenarioIn
from app.services import device_types, devices, scenarios

# клапана нет среди готовых эмуляторов, он собирается в конструкторе
VALVE = DeviceTypeSpec(
    family="valve",
    title="Клапан воды",
    signals=[
        {"name": "position", "title": "Положение", "kind": "property", "control": "list",
         "layout": {"0": "открыт", "1": "перекрыт"}},
        {"name": "close", "title": "Перекрыть воду", "kind": "capability", "control": "switch",
         "affects": "position"},
        {"name": "pressure", "title": "Давление", "kind": "property", "control": "counter",
         "measure": "бар", "min": 0, "max": 10, "default": 3},
    ],
)

DEVICES = (
    ("leak", "Датчик протечки в ванной"),
    ("valve", "Клапан воды"),
    ("light", "Свет в коридоре"),
    ("thermostat", "Термостат в гостиной"),
    ("barrier", "Шлагбаум во дворе"),
    ("counter", "Счётчик электроэнергии"),
)


def _scenarios(ids: dict[str, int]) -> list[dict]:
    return [
        {
            "title": "Протечка: перекрыть воду",
            "blocks": [{"id": "demo_valve", "deviceId": ids["valve"]}],
            "conditions": [{"id": "demo_leak", "type": "leak", "action": "on"}],
        },
        {
            # свет и отопление выключаются одновременно: один столбец
            "title": "Никого нет дома",
            "blocks": [
                {"id": "demo_light_away", "deviceId": ids["light"], "col": 0},
                {"id": "demo_heat_away", "deviceId": ids["thermostat"], "col": 0},
            ],
            "conditions": [{"id": "demo_away", "type": "away", "action": "off"}],
        },
        {
            "title": "Гость у шлагбаума: включить свет",
            "blocks": [{"id": "demo_light_door", "deviceId": ids["light"]}],
            "conditions": [{"id": "demo_door", "type": "door", "action": "on"}],
        },
    ]


def seed_if_empty(session: Session) -> bool:
    has_devices = session.scalar(select(func.count(Device.id)))
    has_scenarios = session.scalar(select(func.count(Scenario.id)))
    if has_devices or has_scenarios:
        return False
    if not registry.is_known(VALVE.family):
        device_types.create_type(session, VALVE)
    ids = {}
    for family, name in DEVICES:
        ids[family] = devices.create_device(session, DeviceCreate(name=name, family=family)).id
    for data in _scenarios(ids):
        scenarios.create_scenario(session, ScenarioIn.model_validate(data))
    return True
