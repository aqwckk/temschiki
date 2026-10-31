from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Scenario
from app.scenarios.engine import engine
from app.schemas import ScenarioIn, ScenarioRead, ScenarioRunRead
from app.services import journal
from app.services import scenarios as service

router = APIRouter(prefix="/api/scenarios", tags=["scenarios"])


def get_existing_scenario(scenario_id: int, session: Session = Depends(get_session)) -> Scenario:
    scenario = service.get_scenario(session, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="сценарий не найден")
    return scenario


@router.get("", response_model=list[ScenarioRead])
def list_scenarios(session: Session = Depends(get_session)):
    return service.list_scenarios(session)


@router.get("/{scenario_id}", response_model=ScenarioRead)
def get_scenario(scenario: Scenario = Depends(get_existing_scenario)):
    return scenario


@router.post("", response_model=ScenarioRead, status_code=status.HTTP_201_CREATED)
def create_scenario(data: ScenarioIn, session: Session = Depends(get_session)):
    return service.create_scenario(session, data)


@router.put("/{scenario_id}", response_model=ScenarioRead)
def update_scenario(
    data: ScenarioIn,
    scenario: Scenario = Depends(get_existing_scenario),
    session: Session = Depends(get_session),
):
    return service.update_scenario(session, scenario, data)


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scenario(
    scenario: Scenario = Depends(get_existing_scenario),
    session: Session = Depends(get_session),
):
    service.delete_scenario(session, scenario)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{scenario_id}/run", status_code=status.HTTP_202_ACCEPTED)
def run_scenario(scenario: Scenario = Depends(get_existing_scenario)):
    engine.run_now(scenario)
    return {"status": "started"}


@router.get("/{scenario_id}/runs", response_model=list[ScenarioRunRead])
def list_scenario_runs(
    scenario: Scenario = Depends(get_existing_scenario),
    session: Session = Depends(get_session),
):
    return journal.list_runs(session, scenario_id=scenario.id)
