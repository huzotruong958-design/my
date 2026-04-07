from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.db.session import get_session
from app.schemas.common import AgentProbePayload
from app.services.workflow import workflow_service

router = APIRouter()


@router.post("/probe-agent")
def probe_agent(payload: AgentProbePayload, session: Session = Depends(get_session)):
    if payload.agent_type not in workflow_service.steps:
        raise HTTPException(status_code=400, detail="Unknown agent type")
    return workflow_service.probe_agent(
        session=session,
        tenant_id=payload.tenant_id,
        agent_type=payload.agent_type,
        state=payload.state,
    )
