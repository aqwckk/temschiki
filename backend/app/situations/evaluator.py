"""Проверка, происходит ли ситуация прямо сейчас."""
from datetime import datetime
from typing import Optional

from app.scenarios.blocks import compare
from app.situations.catalog import Situation

NIGHT_START_HOUR = 22
NIGHT_END_HOUR = 7


def is_active(
    situation: Situation,
    threshold: Optional[float],
    manual_types: set[str],
    states: list[dict],
    now: datetime,
) -> bool:
    if situation.type in manual_types:
        return True
    if situation.night and is_night(now):
        return True
    for rule in situation.sensors:
        limit = _limit(rule, situation, threshold)
        for state in states:
            if state["family"] != rule.family or not state["online"]:
                continue
            if compare(state["values"].get(rule.signal), rule.op, limit):
                return True
    return False


def is_night(now: datetime) -> bool:
    return now.hour >= NIGHT_START_HOUR or now.hour < NIGHT_END_HOUR


def _limit(rule, situation: Situation, threshold: Optional[float]):
    if rule.value is not None:
        return rule.value
    if threshold is not None:
        return threshold
    return situation.value
