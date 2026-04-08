from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlmodel import Session, select

from app.core.config import settings
from app.models.entities import AppSetting
from app.services.secrets import secrets_service


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
    CONTENT_STRATEGY_CONFIG_KEY = "content_strategy_config"
    DESTINATION_HISTORY_KEY = "destination_history"
    AUTO_DESTINATION_BLACKLIST_KEY = "auto_destination_blacklist"
    SENSITIVE_SETTING_KEYS = {
        XIAOHONGSHU_MCP_API_TOKEN_KEY,
        WECHAT_COMPONENT_TICKET_KEY,
        WECHAT_COMPONENT_TOKEN_KEY,
        WECHAT_PRE_AUTH_CODE_KEY,
        WECHAT_LAST_CALLBACK_RAW_XML_KEY,
    }

    def get(self, session: Session, key: str, default: str = "") -> str:
        record = session.exec(select(AppSetting).where(AppSetting.setting_key == key)).first()
        if not record:
            return default
        if key in self.SENSITIVE_SETTING_KEYS:
            return secrets_service.decrypt_if_needed(record.setting_value)
        return record.setting_value

    def set(self, session: Session, key: str, value: str) -> AppSetting:
        record = session.exec(select(AppSetting).where(AppSetting.setting_key == key)).first()
        stored_value = (
            secrets_service.encrypt_if_needed(value)
            if key in self.SENSITIVE_SETTING_KEYS
            else value
        )
        if record:
            record.setting_value = stored_value
            record.updated_at = datetime.utcnow()
        else:
            record = AppSetting(setting_key=key, setting_value=stored_value)
            session.add(record)
        session.commit()
        session.refresh(record)
        return record

    def get_image_provider(self, session: Session) -> str:
        return self.get(session, self.IMAGE_PROVIDER_KEY, settings.image_source_provider)

    def get_content_strategy_config(self, session: Session) -> dict[str, Any]:
        default_config = {
            "departure_city": "郑州",
            "transport_mode": "自驾",
            "max_transport_hours": 3,
            "trip_day_count": 2,
            "trip_nights": 1,
            "no_repeat_months": 3,
            "persona_brief": (
                "林间，第一人称旅行作者，中年父亲，与妻子共同带娃出行；"
                "重视真实体验、低容错率、生活流叙事和高质量攻略感。"
            ),
            "hard_constraints": (
                "必须河南省外；必须小众避人潮；严禁黑名单地点；"
                "优先本地人多游客少、适合周末两天短途的县城/古镇/小城。"
            ),
            "blacklist": [],
            "seasonal_guidance": (
                "根据出发日期提炼时节限定主题，把光线、气味、温度、声音等季节感受贯穿全文。"
            ),
            "title_rules": (
                "标题要包含具体地点或距离、反差或冲突、明确利益点；"
                "长度 22-35 字，不能标题党。"
            ),
            "structure_rules": (
                "文章采用开篇、Day1、Day2、返程、实用信息结构；"
                "每个景点/餐厅需明确地址、价格、时长、交通、评价、tips。"
            ),
            "style_rules": (
                "克制、精准、有画面感；拒绝排比、口号、研究报告腔、感叹号堆砌和虚假信息。"
            ),
            "carry_goods_rules": (
                "仅推荐便携、常温、保质期长且和当地体验直接相关的特产；没有就不写。"
            ),
        }
        raw = self.get(session, self.CONTENT_STRATEGY_CONFIG_KEY, "")
        if not raw:
            return default_config
        try:
            parsed = json.loads(raw)
        except Exception:
            return default_config
        if not isinstance(parsed, dict):
            return default_config
        merged = {**default_config, **parsed}
        merged["blacklist"] = [
            str(item).strip()
            for item in merged.get("blacklist", [])
            if str(item).strip()
        ]
        return merged

    def get_manual_blacklist(self, session: Session) -> list[str]:
        return self.get_content_strategy_config(session).get("blacklist", [])

    def set_content_strategy_config(self, session: Session, config: dict[str, Any]) -> AppSetting:
        normalized = {
            "departure_city": str(config.get("departure_city") or "郑州").strip() or "郑州",
            "transport_mode": str(config.get("transport_mode") or "自驾").strip() or "自驾",
            "max_transport_hours": float(config.get("max_transport_hours") or 3),
            "trip_day_count": int(config.get("trip_day_count") or 2),
            "trip_nights": int(config.get("trip_nights") or 1),
            "no_repeat_months": max(1, int(config.get("no_repeat_months") or 3)),
            "persona_brief": str(config.get("persona_brief") or "").strip(),
            "hard_constraints": str(config.get("hard_constraints") or "").strip(),
            "blacklist": [
                str(item).strip()
                for item in config.get("blacklist", [])
                if str(item).strip()
            ],
            "seasonal_guidance": str(config.get("seasonal_guidance") or "").strip(),
            "title_rules": str(config.get("title_rules") or "").strip(),
            "structure_rules": str(config.get("structure_rules") or "").strip(),
            "style_rules": str(config.get("style_rules") or "").strip(),
            "carry_goods_rules": str(config.get("carry_goods_rules") or "").strip(),
        }
        return self.set(
            session,
            self.CONTENT_STRATEGY_CONFIG_KEY,
            json.dumps(normalized, ensure_ascii=False),
        )

    def get_destination_history(self, session: Session) -> list[dict[str, Any]]:
        raw = self.get(session, self.DESTINATION_HISTORY_KEY, "[]")
        try:
            parsed = json.loads(raw)
        except Exception:
            return []
        if not isinstance(parsed, list):
            return []
        history: list[dict[str, Any]] = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            destination = str(item.get("destination") or "").strip()
            selected_at = str(item.get("selected_at") or "").strip()
            if not destination or not selected_at:
                continue
            history.append(
                {
                    "destination": destination,
                    "selected_at": selected_at,
                    "job_id": item.get("job_id"),
                }
            )
        return history

    def get_auto_destination_blacklist(self, session: Session) -> list[str]:
        raw = self.get(session, self.AUTO_DESTINATION_BLACKLIST_KEY, "[]")
        try:
            parsed = json.loads(raw)
        except Exception:
            return []
        if not isinstance(parsed, list):
            return []
        return [str(item).strip() for item in parsed if str(item).strip()]

    def set_auto_destination_blacklist(self, session: Session, destinations: list[str]) -> AppSetting:
        normalized: list[str] = []
        seen: set[str] = set()
        for item in destinations:
            destination = str(item).strip()
            folded = destination.casefold()
            if not destination or folded in seen:
                continue
            seen.add(folded)
            normalized.append(destination)
        return self.set(
            session,
            self.AUTO_DESTINATION_BLACKLIST_KEY,
            json.dumps(normalized, ensure_ascii=False),
        )

    def set_destination_history(self, session: Session, history: list[dict[str, Any]]) -> AppSetting:
        return self.set(
            session,
            self.DESTINATION_HISTORY_KEY,
            json.dumps(history, ensure_ascii=False),
        )

    def get_recent_destinations(self, session: Session, *, months: int = 3) -> list[str]:
        cutoff = datetime.utcnow().replace(microsecond=0) - __import__("datetime").timedelta(days=max(1, months) * 30)
        recent: list[str] = []
        seen: set[str] = set()
        for item in self.get_destination_history(session):
            try:
                selected_at = datetime.fromisoformat(str(item.get("selected_at") or ""))
            except ValueError:
                continue
            destination = str(item.get("destination") or "").strip()
            normalized = destination.casefold()
            if not destination or normalized in seen or selected_at < cutoff:
                continue
            seen.add(normalized)
            recent.append(destination)
        return recent

    def refresh_auto_destination_blacklist(self, session: Session, *, months: int = 3) -> list[str]:
        recent = self.get_recent_destinations(session, months=months)
        self.set_auto_destination_blacklist(session, recent)
        return recent

    def record_selected_destination(self, session: Session, *, destination: str, job_id: int | None) -> None:
        normalized_destination = destination.strip()
        if not normalized_destination:
            return
        history = self.get_destination_history(session)
        filtered = [item for item in history if str(item.get("destination") or "").strip().casefold() != normalized_destination.casefold()]
        filtered.insert(
            0,
            {
                "destination": normalized_destination,
                "selected_at": datetime.utcnow().replace(microsecond=0).isoformat(),
                "job_id": job_id,
            },
        )
        self.set_destination_history(session, filtered[:200])
        months = int(self.get_content_strategy_config(session).get("no_repeat_months") or 3)
        self.refresh_auto_destination_blacklist(session, months=months)

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
        timeout_raw = self.get(session, self.XIAOHONGSHU_MCP_TIMEOUT_SECONDS_KEY, "60")
        try:
            timeout_seconds = int(timeout_raw)
        except ValueError:
            timeout_seconds = 60
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
