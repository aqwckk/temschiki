"""Доступы команды к стенду Ujin из доступы.json."""
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class UjinDevice:
    family: str
    serialnumber: str
    ext: str
    model: str
    publish_class: str
    apartment_id: str


@dataclass(frozen=True)
class Employee:
    """Сотрудник УК: от его имени устройства публикуют сигналы и читаются обратно."""

    login: str
    password: str
    app: str


@dataclass(frozen=True)
class UjinCredentials:
    api_base: str
    ust: str
    apartment_id: str
    employee: Optional[Employee]
    devices: list[UjinDevice]

    def device_for(self, family: str) -> Optional[UjinDevice]:
        for device in self.devices:
            if device.family == family:
                return device
        return None


def load(path: Path) -> Optional[UjinCredentials]:
    # docker на месте отсутствующего файла создает пустую папку
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    resident = data["residents"][0]
    devices = [
        UjinDevice(
            family=item["family"],
            serialnumber=str(item["sn"]),
            ext=item["ext"],
            model=item["model"],
            publish_class=item["publish_class"],
            apartment_id=str(item.get("apartment_id") or resident["apartment_id"]),
        )
        for item in data["devices"]
    ]
    employee = None
    raw_employee = data.get("employee") or {}
    if raw_employee.get("login") and raw_employee.get("password"):
        employee = Employee(
            login=raw_employee["login"],
            password=raw_employee["password"],
            app=raw_employee.get("app", ""),
        )
    return UjinCredentials(
        api_base=data.get("api_base", ""),
        ust=resident["ust"],
        apartment_id=str(resident["apartment_id"]),
        employee=employee,
        devices=devices,
    )
