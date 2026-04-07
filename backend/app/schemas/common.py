from typing import Any, Literal

from pydantic import BaseModel, Field


AGENT_TYPES = [
    "researcher",
    "fact_checker",
    "writer",
    "formatter",
    "editor",
    "image_editor",
    "publisher",
]


class TravelRequest(BaseModel):
    tenant_id: int
    account_id: int
    start_date: str
    end_date: str
    audience_profile: str | None = None
    style_preset: str | None = None
    extra_constraints: str | None = None


class ModelConfigPayload(BaseModel):
    provider: str
    credential_id: int | None = None
    model_name: str
    temperature: float = 0.2
    max_tokens: int = 3000
    timeout_seconds: int = 60
    enabled: bool = True
    extra_params: dict[str, Any] = Field(default_factory=dict)


class AgentModelConfigPayload(BaseModel):
    default_model: ModelConfigPayload | None = None
    agents: dict[str, ModelConfigPayload]


class CredentialPayload(BaseModel):
    provider: str
    label: str
    api_key: str
    base_url: str | None = None


class SchedulePayload(BaseModel):
    tenant_id: int
    official_account_id: int
    name: str
    cron: str
    timezone: str = "Asia/Shanghai"
    time_window_start: str = "08:00"
    time_window_end: str = "22:00"
    enabled: bool = True


class ScheduleUpdatePayload(BaseModel):
    name: str | None = None
    cron: str | None = None
    timezone: str | None = None
    time_window_start: str | None = None
    time_window_end: str | None = None
    enabled: bool | None = None


class JobReplayPayload(BaseModel):
    override_account_id: int | None = None


class PublishExecutePayload(BaseModel):
    dry_run: bool = True


class ComponentTicketPayload(BaseModel):
    component_verify_ticket: str


class ComponentCallbackMockPayload(BaseModel):
    info_type: str = "component_verify_ticket"
    component_verify_ticket: str = "mock-component-ticket"
    authorizer_appid: str | None = None


class AccountCreatePayload(BaseModel):
    tenant_id: int
    display_name: str
    wechat_app_id: str
    principal_name: str | None = None


class SearchPreviewPayload(BaseModel):
    destination: str
    start_date: str
    end_date: str
    intent: Literal[
        "destination_overview",
        "transport",
        "attractions",
        "food",
        "hotel",
        "season_weather",
        "avoidance_tips",
    ] = "destination_overview"


class ImageProviderUpdatePayload(BaseModel):
    provider: str


class ExternalImageItemPayload(BaseModel):
    url: str
    tag: str = "landmark"
    title: str | None = None
    source_page: str | None = None


class ExternalImageManifestPayload(BaseModel):
    items: list[ExternalImageItemPayload] = Field(default_factory=list)


class XiaohongshuSeedUrlsPayload(BaseModel):
    urls: list[str] = Field(default_factory=list)


class XiaohongshuPreviewPayload(BaseModel):
    urls: list[str] = Field(default_factory=list)
    destination: str | None = None
    title: str | None = None
    summary: str | None = None
    limit: int = 8


class XiaohongshuMcpConfigPayload(BaseModel):
    enabled: bool = False
    endpoint: str = ""
    api_token: str = ""
    auth_header: str = "Authorization"
    timeout_seconds: int = 30


class AgentProbePayload(BaseModel):
    tenant_id: int
    agent_type: Literal[
        "researcher",
        "fact_checker",
        "writer",
        "formatter",
        "editor",
        "image_editor",
        "publisher",
    ]
    state: dict[str, Any] = Field(default_factory=dict)
