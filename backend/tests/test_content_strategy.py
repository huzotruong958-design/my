from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlmodel import SQLModel, Session, create_engine, select

from app.models import entities  # noqa: F401
from app.models.entities import AppSetting, ArticleJob, ModelCredential
from app.services.app_settings import app_settings_service
from app.services.secrets import secrets_service
from app.services.workflow import WorkflowService


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db_session:
        yield db_session


def test_content_strategy_roundtrip_and_auto_blacklist_refresh(session: Session) -> None:
    app_settings_service.set_content_strategy_config(
        session,
        {
            "departure_city": "郑州",
            "transport_mode": "自驾",
            "max_transport_hours": 3,
            "trip_day_count": 2,
            "trip_nights": 1,
            "no_repeat_months": 3,
            "persona_brief": "测试人设",
            "hard_constraints": "测试约束",
            "blacklist": ["西安", "南京"],
            "seasonal_guidance": "春天",
            "title_rules": "标题规则",
            "structure_rules": "结构规则",
            "style_rules": "风格规则",
            "carry_goods_rules": "特产规则",
        },
    )

    config = app_settings_service.get_content_strategy_config(session)
    assert config["departure_city"] == "郑州"
    assert config["no_repeat_months"] == 3
    assert config["blacklist"] == ["西安", "南京"]

    app_settings_service.set_destination_history(
        session,
        [
            {
                "destination": "安吉",
                "selected_at": datetime.utcnow().replace(microsecond=0).isoformat(),
                "job_id": 1,
            },
            {
                "destination": "台州",
                "selected_at": (datetime.utcnow() - timedelta(days=120)).replace(microsecond=0).isoformat(),
                "job_id": 2,
            },
        ],
    )

    recent = app_settings_service.refresh_auto_destination_blacklist(session, months=3)
    assert recent == ["安吉"]
    assert app_settings_service.get_auto_destination_blacklist(session) == ["安吉"]


def test_record_selected_destination_updates_history_and_auto_blacklist(session: Session) -> None:
    app_settings_service.set_content_strategy_config(session, {"no_repeat_months": 3, "blacklist": ["手工地点"]})

    app_settings_service.record_selected_destination(session, destination="榆林", job_id=11)
    app_settings_service.record_selected_destination(session, destination="榆林", job_id=12)
    app_settings_service.record_selected_destination(session, destination="赤峰", job_id=13)

    history = app_settings_service.get_destination_history(session)
    assert [item["destination"] for item in history[:2]] == ["赤峰", "榆林"]
    assert app_settings_service.get_auto_destination_blacklist(session) == ["赤峰", "榆林"]
    assert app_settings_service.get_manual_blacklist(session) == ["手工地点"]


def test_retry_researcher_if_repeated_replaces_destination(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    service = WorkflowService()
    state = {
        "content_strategy_config": {"no_repeat_months": 3},
        "recent_destinations": ["安吉"],
        "auto_blacklist": ["安吉"],
    }
    repeated_output = {"result": {"destination": "安吉"}, "risk_flags": []}
    retry_output = {"result": {"destination": "榆林"}, "risk_flags": []}

    monkeypatch.setattr(service, "_execute_agent", lambda agent_type, retry_state, model_info: retry_output)

    result = service._retry_researcher_if_repeated(
        session=session,
        job=ArticleJob(tenant_id=1, official_account_id=1, start_date="2026-04-10", end_date="2026-04-12"),
        state=state,
        model_info={"provider": "gemini", "model_name": "gemini-3-flash-preview"},
        output=repeated_output,
    )

    assert result["result"]["destination"] == "榆林"
    assert "replaced_repeated_destination:安吉" in result["risk_flags"]


def test_retry_researcher_if_repeated_raises_when_destination_still_repeated(
    session: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = WorkflowService()
    state = {
        "content_strategy_config": {"no_repeat_months": 3},
        "recent_destinations": ["安吉"],
        "auto_blacklist": ["安吉"],
    }
    repeated_output = {"result": {"destination": "安吉"}, "risk_flags": []}

    monkeypatch.setattr(service, "_execute_agent", lambda agent_type, retry_state, model_info: repeated_output)

    with pytest.raises(RuntimeError, match="repeated destination"):
        service._retry_researcher_if_repeated(
            session=session,
            job=ArticleJob(tenant_id=1, official_account_id=1, start_date="2026-04-10", end_date="2026-04-12"),
            state=state,
            model_info={"provider": "gemini", "model_name": "gemini-3-flash-preview"},
            output=repeated_output,
        )


def test_sensitive_values_are_encrypted_on_write_and_plaintext_is_backward_compatible(session: Session) -> None:
    app_settings_service.set(session, app_settings_service.WECHAT_COMPONENT_TOKEN_KEY, "component-secret-token")
    record = session.exec(
        select(AppSetting).where(AppSetting.setting_key == app_settings_service.WECHAT_COMPONENT_TOKEN_KEY)
    ).first()
    assert record is not None
    assert record.setting_value.startswith(secrets_service.prefix)
    assert app_settings_service.get(session, app_settings_service.WECHAT_COMPONENT_TOKEN_KEY) == "component-secret-token"

    legacy = AppSetting(
        setting_key=app_settings_service.XIAOHONGSHU_MCP_API_TOKEN_KEY,
        setting_value="legacy-plain-token",
    )
    session.add(legacy)
    session.commit()
    assert app_settings_service.get(session, app_settings_service.XIAOHONGSHU_MCP_API_TOKEN_KEY) == "legacy-plain-token"

    credential = ModelCredential(
        tenant_id=1,
        provider="gemini",
        label="test",
        api_key_encrypted=secrets_service.encrypt_if_needed("api-key-value"),
    )
    session.add(credential)
    session.commit()
    assert secrets_service.decrypt_if_needed(credential.api_key_encrypted) == "api-key-value"
