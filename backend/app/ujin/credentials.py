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


@dataclass(frozen=True)
class UjinCredentials:
    ust: str
    apartment_id: str
    devices: list[UjinDevice]

    def device_for(self, family: str) -> Optional[UjinDevice]:
        for device in self.devices:
            if device.family == family:
                return device
        return None


def load(path: Path) -> Optional[UjinCredentials]:
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
        )
        for item in data["devices"]
    ]
    return UjinCredentials(ust=resident["ust"], apartment_id=str(resident["apartment_id"]), devices=devices)
