from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db.session import get_session
from app.models.entities import Schedule
from app.schemas.common import SchedulePayload, ScheduleUpdatePayload
from app.services.scheduler import scheduler_service

router = APIRouter()


@router.get("")
def list_schedules(_: Session = Depends(get_session)):
    return scheduler_service.list_schedule_runtime()


@router.post("")
def create_schedule(payload: SchedulePayload, session: Session = Depends(get_session)):
    schedule = Schedule(**payload.model_dump())
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    scheduler_service.register_schedule(schedule)
    return schedule


@router.patch("/{schedule_id}")
def update_schedule(
    schedule_id: int, payload: ScheduleUpdatePayload, session: Session = Depends(get_session)
):
    schedule = session.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(schedule, key, value)
    session.add(schedule)
    session.commit()
    session.refresh(schedule)
    scheduler_service.register_schedule(schedule)
    return schedule


@router.post("/{schedule_id}/run-now")
def run_schedule_now(schedule_id: int, session: Session = Depends(get_session)):
    schedule = session.get(Schedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    scheduler_service.run_scheduled_job(schedule_id, trigger_type="manual")
    return {"ok": True, "schedule_id": schedule_id}
