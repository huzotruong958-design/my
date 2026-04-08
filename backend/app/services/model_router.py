from __future__ import annotations

import json

from sqlmodel import Session, select

from app.models.entities import AgentModelConfig, ModelCredential
from app.services.secrets import secrets_service


DEFAULT_AGENT_MODELS = {
    "researcher": {"provider": "gemini", "model_name": "gemini-3-flash-preview"},
    "fact_checker": {"provider": "gemini", "model_name": "gemini-3-flash-preview"},
    "writer": {"provider": "gemini", "model_name": "gemini-3-pro-preview"},
    "formatter": {"provider": "gemini", "model_name": "gemini-3-flash-preview"},
    "editor": {"provider": "gemini", "model_name": "gemini-3-flash-preview"},
    "image_editor": {"provider": "gemini", "model_name": "gemini-3-flash-preview"},
    "publisher": {"provider": "system", "model_name": "workflow"},
}


class ModelRouter:
    def resolve(self, session: Session, tenant_id: int, agent_type: str) -> dict:
        statement = select(AgentModelConfig).where(
            AgentModelConfig.tenant_id == tenant_id, AgentModelConfig.agent_type == agent_type
        )
        config = session.exec(statement).first()
        if not config:
            return {
                **DEFAULT_AGENT_MODELS[agent_type],
                "temperature": 0.2,
                "max_tokens": 3000,
                "timeout_seconds": 60,
                "extra_params": {},
            }

        credential = None
        if config.credential_id:
            credential = session.get(ModelCredential, config.credential_id)

        return {
            "provider": config.provider,
            "model_name": config.model_name,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
            "timeout_seconds": config.timeout_seconds,
            "extra_params": json.loads(config.extra_params or "{}"),
            "credential": {
                "id": credential.id,
                "label": credential.label,
                "base_url": credential.base_url,
                "api_key": secrets_service.decrypt_if_needed(credential.api_key_encrypted),
            }
            if credential
            else None,
        }


model_router = ModelRouter()
