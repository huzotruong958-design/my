from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlmodel import Field, SQLModel


class JobStatus(StrEnum):
    pending = "pending"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class AccountStatus(StrEnum):
    unauthorized = "unauthorized"
    authorized = "authorized"
    publishable = "publishable"


class Tenant(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    slug: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AppSetting(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    setting_key: str = Field(index=True, unique=True)
    setting_value: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(index=True, foreign_key="tenant.id")
    email: str = Field(index=True, unique=True)
    password_hash: str
    role: str = "tenant_admin"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OfficialAccount(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(index=True, foreign_key="tenant.id")
    display_name: str
    wechat_app_id: str = Field(index=True)
    principal_name: str = ""
    status: AccountStatus = Field(default=AccountStatus.unauthorized)
    publishable: bool = False
    last_refreshed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class WeChatAuthorization(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    official_account_id: int = Field(index=True, foreign_key="officialaccount.id")
    authorizer_app_id: str = Field(index=True)
    authorizer_refresh_token: str
    authorizer_access_token: str
    expires_at: Optional[datetime] = None
    raw_payload: str = "{}"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ModelCredential(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(index=True, foreign_key="tenant.id")
    provider: str
    label: str
    api_key_encrypted: str
    base_url: str = ""
    status: str = "unvalidated"
    last_validated_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentModelConfig(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(index=True, foreign_key="tenant.id")
    agent_type: str = Field(index=True)
    provider: str
    credential_id: Optional[int] = Field(default=None, foreign_key="modelcredential.id")
    model_name: str
    temperature: float = 0.2
    max_tokens: int = 3000
    timeout_seconds: int = 60
    enabled: bool = True
    extra_params: str = "{}"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Schedule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(index=True, foreign_key="tenant.id")
    official_account_id: int = Field(index=True, foreign_key="officialaccount.id")
    name: str
    cron: str
    timezone: str = "Asia/Shanghai"
    time_window_start: str = "08:00"
    time_window_end: str = "22:00"
    enabled: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ScheduleRun(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    schedule_id: int = Field(index=True, foreign_key="schedule.id")
    article_job_id: Optional[int] = Field(default=None, index=True, foreign_key="articlejob.id")
    trigger_type: str = "cron"
    attempt: int = 1
    status: str = "pending"
    message: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ArticleJob(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: int = Field(index=True, foreign_key="tenant.id")
    official_account_id: int = Field(index=True, foreign_key="officialaccount.id")
    schedule_id: Optional[int] = Field(default=None, foreign_key="schedule.id")
    start_date: str
    end_date: str
    destination: str = ""
    status: JobStatus = Field(default=JobStatus.pending)
    payload_json: str = "{}"
    output_json: str = "{}"
    error_message: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class JobStep(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    article_job_id: int = Field(index=True, foreign_key="articlejob.id")
    agent_name: str
    status: str = "pending"
    model_provider: str = ""
    model_name: str = ""
    output_json: str = "{}"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PublishRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    article_job_id: int = Field(index=True, foreign_key="articlejob.id")
    official_account_id: int = Field(index=True, foreign_key="officialaccount.id")
    authorization_mode: str = ""
    draft_id: str = ""
    cover_media_id: str = ""
    thumb_result_json: str = "{}"
    upload_results_json: str = "[]"
    draft_response_json: str = "{}"
    content_media_ids: str = "[]"
    raw_response: str = "{}"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class MediaAsset(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    article_job_id: Optional[int] = Field(default=None, index=True, foreign_key="articlejob.id")
    official_account_id: Optional[int] = Field(default=None, index=True, foreign_key="officialaccount.id")
    asset_type: str
    source_url: str = ""
    local_path: str = ""
    upload_role: str = ""
    wechat_media_id: str = ""
    wechat_url: str = ""
    upload_response_json: str = "{}"
    metadata_json: str = "{}"
    created_at: datetime = Field(default_factory=datetime.utcnow)
