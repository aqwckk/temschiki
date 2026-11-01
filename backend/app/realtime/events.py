"""Формат событий для фронта. Поле type говорит, что произошло."""
from typing import Any

from app.realtime.hub import hub


def snapshot(states: list[dict]) -> dict:
    return {"type": "snapshot", "devices": states}


def publish_signal(device_id: int, name: str, value: Any) -> None:
    hub.publish({"type": "signal", "device_id": device_id, "signal": name, "value": value})


def publish_device_status(device_id: int, online: bool) -> None:
    hub.publish({"type": "device_status", "device_id": device_id, "online": online})


def publish_run(run: dict) -> None:
    hub.publish({"type": "scenario_run", "run": run})


def publish_notification(notification: dict) -> None:
    hub.publish({"type": "notification", "notification": notification})


def publish_emergency(emergency: dict) -> None:
    hub.publish({"type": "emergency_started", "emergency": emergency})


def publish_emergency_ended(emergency_id: int) -> None:
    hub.publish({"type": "emergency_ended", "id": emergency_id})
