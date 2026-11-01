from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Emergency
from app.schemas import EmergencyIn, EmergencyRead, SituationCreate, SituationRead
from app.services import emergencies as emergency_service
from app.services import situations as situation_service
from app.situations import catalog

router = APIRouter(prefix="/api", tags=["situations"])


def get_existing_emergency(emergency_id: int, session: Session = Depends(get_session)) -> Emergency:
    row = emergency_service.get(session, emergency_id)
    if row is None:
        raise HTTPException(status_code=404, detail="ситуация не найдена")
    return row


@router.get("/situations", response_model=list[SituationRead])
def list_situations():
    return catalog.all_situations()


@router.post("/situations", response_model=SituationRead)
def create_situation(data: SituationCreate, session: Session = Depends(get_session)):
    return situation_service.get_or_create(session, data.label)


@router.get("/emergencies", response_model=list[EmergencyRead])
def list_emergencies(session: Session = Depends(get_session)):
    return emergency_service.list_active(session)


@router.post("/emergencies", response_model=EmergencyRead, status_code=status.HTTP_201_CREATED)
def start_emergency(data: EmergencyIn, session: Session = Depends(get_session)):
    return emergency_service.start(session, data)


@router.delete("/emergencies/{emergency_id}", status_code=status.HTTP_204_NO_CONTENT)
def end_emergency(
    row: Emergency = Depends(get_existing_emergency),
    session: Session = Depends(get_session),
):
    emergency_service.end(session, row)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
