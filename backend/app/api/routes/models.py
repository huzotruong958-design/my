import json
from datetime import datetime

from fastapi import APIRouter, Depends
from sqlmodel import Session, delete, select

from app.db.session import get_session
from app.models.entities import AgentModelConfig, ModelCredential
from app.schemas.common import AgentModelConfigPayload, CredentialPayload

router = APIRouter()


def serialize_credential(credential: ModelCredential) -> dict:
    masked = ""
    if credential.api_key_encrypted:
        key = credential.api_key_encrypted
        masked = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "****"
    return {
        "id": credential.id,
        "tenant_id": credential.tenant_id,
        "provider": credential.provider,
        "label": credential.label,
        "base_url": credential.base_url,
        "status": credential.status,
        "last_validated_at": credential.last_validated_at,
        "api_key_masked": masked,
        "has_api_key": bool(credential.api_key_encrypted),
        "created_at": credential.created_at,
    }


@router.get("/providers")
def list_providers():
    return [
        {"id": "gemini", "label": "Google Gemini"},
        {"id": "openai-compatible", "label": "OpenAI Compatible"},
        {"id": "anthropic", "label": "Anthropic"},
    ]


@router.get("/tenants/{tenant_id}/credentials")
def list_credentials(tenant_id: int, session: Session = Depends(get_session)):
    credentials = session.exec(
        select(ModelCredential).where(ModelCredential.tenant_id == tenant_id)
    ).all()
    return [serialize_credential(item) for item in credentials]


@router.post("/tenants/{tenant_id}/credentials")
def create_credential(
    tenant_id: int, payload: CredentialPayload, session: Session = Depends(get_session)
):
    credential = ModelCredential(
        tenant_id=tenant_id,
        provider=payload.provider,
        label=payload.label,
        api_key_encrypted=payload.api_key,
        base_url=payload.base_url or "",
        status="validated",
        last_validated_at=datetime.utcnow(),
    )
    session.add(credential)
    session.commit()
    session.refresh(credential)
    return serialize_credential(credential)


@router.post("/tenants/{tenant_id}/credentials/{credential_id}/validate")
def validate_credential(tenant_id: int, credential_id: int, session: Session = Depends(get_session)):
    credential = session.get(ModelCredential, credential_id)
    if not credential or credential.tenant_id != tenant_id:
        return {"ok": False}
    credential.status = "validated"
    credential.last_validated_at = datetime.utcnow()
    session.add(credential)
    session.commit()
    return {"ok": True, "credential": serialize_credential(credential)}


@router.get("/tenants/{tenant_id}/agent-configs")
def get_agent_configs(tenant_id: int, session: Session = Depends(get_session)):
    return session.exec(select(AgentModelConfig).where(AgentModelConfig.tenant_id == tenant_id)).all()


@router.get("/tenants/{tenant_id}/agent-configs/effective")
def get_effective_agent_configs(tenant_id: int, session: Session = Depends(get_session)):
    configs = session.exec(select(AgentModelConfig).where(AgentModelConfig.tenant_id == tenant_id)).all()
    return {
        item.agent_type: {
            "provider": item.provider,
            "credential_id": item.credential_id,
            "model_name": item.model_name,
            "temperature": item.temperature,
            "max_tokens": item.max_tokens,
            "timeout_seconds": item.timeout_seconds,
            "enabled": item.enabled,
            "extra_params": json.loads(item.extra_params or "{}"),
        }
        for item in configs
    }


@router.put("/tenants/{tenant_id}/agent-configs")
def save_agent_configs(
    tenant_id: int, payload: AgentModelConfigPayload, session: Session = Depends(get_session)
):
    session.exec(delete(AgentModelConfig).where(AgentModelConfig.tenant_id == tenant_id))
    for agent_type, config in payload.agents.items():
        session.add(
            AgentModelConfig(
                tenant_id=tenant_id,
                agent_type=agent_type,
                provider=config.provider,
                credential_id=config.credential_id,
                model_name=config.model_name,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                timeout_seconds=config.timeout_seconds,
                enabled=config.enabled,
                extra_params=json.dumps(config.extra_params),
            )
        )
    session.commit()
    return {"ok": True}


@router.get("/tenants/{tenant_id}/readiness")
def model_readiness(tenant_id: int, session: Session = Depends(get_session)):
    credentials = session.exec(
        select(ModelCredential).where(ModelCredential.tenant_id == tenant_id)
    ).all()
    configs = session.exec(select(AgentModelConfig).where(AgentModelConfig.tenant_id == tenant_id)).all()
    return {
        "tenant_id": tenant_id,
        "credential_count": len(credentials),
        "validated_credentials": sum(1 for item in credentials if item.status == "validated"),
        "configured_agents": [item.agent_type for item in configs if item.enabled],
        "ready_for_real_llm": any(item.status == "validated" for item in credentials),
    }
