from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from app.core.config import settings
from app.models.entities import AppSetting


class AppSettingsService:
    IMAGE_PROVIDER_KEY = "image_source_provider"
    EXTERNAL_IMAGE_MANIFEST_KEY = "external_image_manifest"
    XIAOHONGSHU_SEED_URLS_KEY = "xiaohongshu_seed_urls"
    XIAOHONGSHU_MCP_ENDPOINT_KEY = "xiaohongshu_mcp_endpoint"
    XIAOHONGSHU_MCP_API_TOKEN_KEY = "xiaohongshu_mcp_api_token"
    XIAOHONGSHU_MCP_AUTH_HEADER_KEY = "xiaohongshu_mcp_auth_header"
    XIAOHONGSHU_MCP_TIMEOUT_SECONDS_KEY = "xiaohongshu_mcp_timeout_seconds"
    XIAOHONGSHU_MCP_ENABLED_KEY = "xiaohongshu_mcp_enabled"
    XIAOHONGSHU_MCP_LAST_PROBE_KEY = "xiaohongshu_mcp_last_probe"
    WECHAT_COMPONENT_TICKET_KEY = "wechat_component_verify_ticket"
    WECHAT_COMPONENT_TOKEN_KEY = "wechat_component_access_token"
    WECHAT_COMPONENT_TOKEN_EXPIRES_AT_KEY = "wechat_component_access_token_expires_at"
    WECHAT_PRE_AUTH_CODE_KEY = "wechat_pre_auth_code"
    WECHAT_PRE_AUTH_CODE_EXPIRES_AT_KEY = "wechat_pre_auth_code_expires_at"
    WECHAT_LAST_CALLBACK_INFO_TYPE_KEY = "wechat_last_callback_info_type"
    WECHAT_LAST_CALLBACK_AT_KEY = "wechat_last_callback_at"
    WECHAT_LAST_CALLBACK_RAW_XML_KEY = "wechat_last_callback_raw_xml"

    def get(self, session: Session, key: str, default: str = "") -> str:
        record = session.exec(select(AppSetting).where(AppSetting.setting_key == key)).first()
        return record.setting_value if record else default

    def set(self, session: Session, key: str, value: str) -> AppSetting:
        record = session.exec(select(AppSetting).where(AppSetting.setting_key == key)).first()
        if record:
            record.setting_value = value
            record.updated_at = datetime.utcnow()
        else:
            record = AppSetting(setting_key=key, setting_value=value)
            session.add(record)
        session.commit()
        session.refresh(record)
        return record

    def get_image_provider(self, session: Session) -> str:
        return self.get(session, self.IMAGE_PROVIDER_KEY, settings.image_source_provider)

    def get_external_image_manifest(self, session: Session) -> list[dict[str, Any]]:
        value = self.get(session, self.EXTERNAL_IMAGE_MANIFEST_KEY, "[]")
        try:
            parsed = __import__("json").loads(value)
        except Exception:
            return []
        return parsed if isinstance(parsed, list) else []

    def set_external_image_manifest(self, session: Session, manifest: list[dict[str, Any]]) -> AppSetting:
        return self.set(
            session,
            self.EXTERNAL_IMAGE_MANIFEST_KEY,
            __import__("json").dumps(manifest, ensure_ascii=False),
        )

    def get_xiaohongshu_seed_urls(self, session: Session) -> list[str]:
        value = self.get(session, self.XIAOHONGSHU_SEED_URLS_KEY, "[]")
        try:
            parsed = __import__("json").loads(value)
        except Exception:
            return []
        if not isinstance(parsed, list):
            return []
        return [str(item).strip() for item in parsed if str(item).strip()]

    def set_xiaohongshu_seed_urls(self, session: Session, urls: list[str]) -> AppSetting:
        normalized = [str(item).strip() for item in urls if str(item).strip()]
        return self.set(
            session,
            self.XIAOHONGSHU_SEED_URLS_KEY,
            __import__("json").dumps(normalized, ensure_ascii=False),
        )

    def get_xiaohongshu_mcp_config(self, session: Session) -> dict[str, Any]:
        timeout_raw = self.get(session, self.XIAOHONGSHU_MCP_TIMEOUT_SECONDS_KEY, "30")
        try:
            timeout_seconds = int(timeout_raw)
        except ValueError:
            timeout_seconds = 30
        enabled = self.get(session, self.XIAOHONGSHU_MCP_ENABLED_KEY, "false").lower() == "true"
        last_probe_raw = self.get(session, self.XIAOHONGSHU_MCP_LAST_PROBE_KEY, "{}")
        try:
            last_probe = __import__("json").loads(last_probe_raw)
        except Exception:
            last_probe = {}
        return {
            "enabled": enabled,
            "endpoint": self.get(session, self.XIAOHONGSHU_MCP_ENDPOINT_KEY, "").strip(),
            "api_token": self.get(session, self.XIAOHONGSHU_MCP_API_TOKEN_KEY, "").strip(),
            "auth_header": self.get(session, self.XIAOHONGSHU_MCP_AUTH_HEADER_KEY, "Authorization").strip()
            or "Authorization",
            "timeout_seconds": timeout_seconds,
            "last_probe": last_probe if isinstance(last_probe, dict) else {},
        }

    def set_xiaohongshu_mcp_config(
        self,
        session: Session,
        *,
        enabled: bool,
        endpoint: str,
        api_token: str,
        auth_header: str,
        timeout_seconds: int,
    ) -> None:
        self.set(session, self.XIAOHONGSHU_MCP_ENABLED_KEY, "true" if enabled else "false")
        self.set(session, self.XIAOHONGSHU_MCP_ENDPOINT_KEY, endpoint.strip())
        self.set(session, self.XIAOHONGSHU_MCP_API_TOKEN_KEY, api_token.strip())
        self.set(session, self.XIAOHONGSHU_MCP_AUTH_HEADER_KEY, auth_header.strip() or "Authorization")
        self.set(session, self.XIAOHONGSHU_MCP_TIMEOUT_SECONDS_KEY, str(timeout_seconds))

    def set_xiaohongshu_mcp_last_probe(self, session: Session, payload: dict[str, Any]) -> AppSetting:
        return self.set(
            session,
            self.XIAOHONGSHU_MCP_LAST_PROBE_KEY,
            __import__("json").dumps(payload, ensure_ascii=False),
        )

    def get_datetime(self, session: Session, key: str) -> datetime | None:
        value = self.get(session, key, "")
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def set_datetime(self, session: Session, key: str, value: datetime) -> AppSetting:
        return self.set(session, key, value.isoformat())

    def get_wechat_component_state(self, session: Session) -> dict[str, Any]:
        return {
            "component_verify_ticket": self.get(session, self.WECHAT_COMPONENT_TICKET_KEY, ""),
            "component_access_token": self.get(session, self.WECHAT_COMPONENT_TOKEN_KEY, ""),
            "component_access_token_expires_at": self.get_datetime(
                session, self.WECHAT_COMPONENT_TOKEN_EXPIRES_AT_KEY
            ),
            "pre_auth_code": self.get(session, self.WECHAT_PRE_AUTH_CODE_KEY, ""),
            "pre_auth_code_expires_at": self.get_datetime(
                session, self.WECHAT_PRE_AUTH_CODE_EXPIRES_AT_KEY
            ),
            "last_callback_info_type": self.get(session, self.WECHAT_LAST_CALLBACK_INFO_TYPE_KEY, ""),
            "last_callback_at": self.get_datetime(session, self.WECHAT_LAST_CALLBACK_AT_KEY),
            "last_callback_raw_xml": self.get(session, self.WECHAT_LAST_CALLBACK_RAW_XML_KEY, ""),
        }


app_settings_service = AppSettingsService()
