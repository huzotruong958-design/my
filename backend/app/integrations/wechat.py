from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

import httpx
from sqlmodel import Session

from app.core.config import settings
from app.services.app_settings import app_settings_service


class WeChatIntegration:
    component_api_base = "https://api.weixin.qq.com/cgi-bin/component/api"

    def config_status(self) -> dict:
        return {
            "component_app_id_configured": bool(settings.wechat_component_app_id),
            "component_app_secret_configured": bool(settings.wechat_component_app_secret),
            "component_token_configured": bool(settings.wechat_component_token),
            "component_aes_key_configured": bool(settings.wechat_component_aes_key),
            "callback_base_url": settings.wechat_callback_base_url,
            "ready_for_real_auth": all(
                [
                    settings.wechat_component_app_id,
                    settings.wechat_component_app_secret,
                    settings.wechat_component_token,
                    settings.wechat_component_aes_key,
                ]
            ),
        }

    def component_state(self, session: Session) -> dict:
        state = app_settings_service.get_wechat_component_state(session)
        now = datetime.utcnow()
        token_expires_at = state["component_access_token_expires_at"]
        pre_auth_expires_at = state["pre_auth_code_expires_at"]
        last_callback_at = state["last_callback_at"]
        return {
            **self.config_status(),
            "has_component_verify_ticket": bool(state["component_verify_ticket"]),
            "has_component_access_token": bool(state["component_access_token"]),
            "component_access_token_expires_at": token_expires_at.isoformat()
            if token_expires_at
            else "",
            "component_access_token_valid": bool(token_expires_at and token_expires_at > now),
            "has_pre_auth_code": bool(state["pre_auth_code"]),
            "pre_auth_code_expires_at": pre_auth_expires_at.isoformat() if pre_auth_expires_at else "",
            "pre_auth_code_valid": bool(pre_auth_expires_at and pre_auth_expires_at > now),
            "last_callback_info_type": state["last_callback_info_type"],
            "last_callback_at": last_callback_at.isoformat() if last_callback_at else "",
            "last_callback_raw_xml": state["last_callback_raw_xml"],
        }

    def endpoint_blueprint(self) -> dict:
        return {
            "component_access_token": {
                "method": "POST",
                "url": f"{self.component_api_base}/component_token",
                "body": {
                    "component_appid": settings.wechat_component_app_id or "<component_appid>",
                    "component_appsecret": "<configured-secret>" if settings.wechat_component_app_secret else "<missing>",
                    "component_verify_ticket": "<latest_ticket_from_wechat_push>",
                },
            },
            "pre_auth_code": {
                "method": "POST",
                "url": f"{self.component_api_base}/create_preauthcode?component_access_token=<component_access_token>",
                "body": {
                    "component_appid": settings.wechat_component_app_id or "<component_appid>",
                },
            },
            "query_auth": {
                "method": "POST",
                "url": f"{self.component_api_base}/query_auth?component_access_token=<component_access_token>",
                "body": {
                    "component_appid": settings.wechat_component_app_id or "<component_appid>",
                    "authorization_code": "<auth_code>",
                },
            },
            "authorizer_token": {
                "method": "POST",
                "url": f"{self.component_api_base}/authorizer_token?component_access_token=<component_access_token>",
                "body": {
                    "component_appid": settings.wechat_component_app_id or "<component_appid>",
                    "authorizer_appid": "<authorizer_appid>",
                    "authorizer_refresh_token": "<authorizer_refresh_token>",
                },
            },
            "upload_image_for_article": {
                "method": "POST",
                "url": "https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token=<authorizer_access_token>",
                "body": {"media": "<multipart-file>"},
            },
            "upload_thumb_media": {
                "method": "POST",
                "url": "https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=<authorizer_access_token>&type=thumb",
                "body": {"media": "<multipart-file>"},
            },
            "add_draft": {
                "method": "POST",
                "url": "https://api.weixin.qq.com/cgi-bin/draft/add?access_token=<authorizer_access_token>",
                "body": {"articles": ["<normalized_article_payload>"]},
            },
        }

    def build_authorization_url(self, tenant_id: int, pre_auth_code: str | None = None) -> str:
        redirect_uri = (
            f"{settings.wechat_callback_base_url.rstrip('/')}"
            f"/api/accounts/wechat/auth/callback?tenant_id={tenant_id}"
        )
        params = urlencode(
            {
                "component_appid": settings.wechat_component_app_id or "demo-component-app-id",
                "pre_auth_code": pre_auth_code or "mock-pre-auth-code",
                "redirect_uri": redirect_uri,
            }
        )
        return f"https://mp.weixin.qq.com/cgi-bin/componentloginpage?{params}"

    def build_component_access_token_request(self) -> dict:
        blueprint = self.endpoint_blueprint()["component_access_token"]
        return deepcopy(blueprint)

    def build_pre_auth_code_request(self) -> dict:
        blueprint = self.endpoint_blueprint()["pre_auth_code"]
        return deepcopy(blueprint)

    def build_query_auth_request(self, auth_code: str) -> dict:
        blueprint = deepcopy(self.endpoint_blueprint()["query_auth"])
        blueprint["body"]["authorization_code"] = auth_code
        return blueprint

    def build_authorizer_token_refresh_request(
        self, authorizer_appid: str, authorizer_refresh_token: str
    ) -> dict:
        blueprint = deepcopy(self.endpoint_blueprint()["authorizer_token"])
        blueprint["body"]["authorizer_appid"] = authorizer_appid
        blueprint["body"]["authorizer_refresh_token"] = authorizer_refresh_token
        return blueprint

    def _post_json(self, url: str, payload: dict) -> dict:
        with httpx.Client(timeout=20) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            return response.json()

    def fetch_component_access_token(self, component_verify_ticket: str) -> dict:
        request = self.build_component_access_token_request()
        request["body"]["component_verify_ticket"] = component_verify_ticket
        return self._post_json(request["url"], request["body"])

    def store_component_verify_ticket(self, session: Session, component_verify_ticket: str) -> dict:
        app_settings_service.set(
            session,
            app_settings_service.WECHAT_COMPONENT_TICKET_KEY,
            component_verify_ticket,
        )
        return self.component_state(session)

    def refresh_component_access_token(self, session: Session) -> dict:
        state = app_settings_service.get_wechat_component_state(session)
        component_verify_ticket = state["component_verify_ticket"]
        if not component_verify_ticket:
            raise ValueError("Component verify ticket is missing.")
        payload = self.fetch_component_access_token(component_verify_ticket)
        access_token = payload.get("component_access_token", "")
        expires_in = int(payload.get("expires_in", 7200))
        expires_at = datetime.utcnow() + timedelta(seconds=max(expires_in - 300, 60))
        app_settings_service.set(session, app_settings_service.WECHAT_COMPONENT_TOKEN_KEY, access_token)
        app_settings_service.set_datetime(
            session,
            app_settings_service.WECHAT_COMPONENT_TOKEN_EXPIRES_AT_KEY,
            expires_at,
        )
        return {
            "component_access_token": access_token,
            "expires_at": expires_at.isoformat(),
            "raw_response": payload,
        }

    def get_valid_component_access_token(self, session: Session) -> str:
        state = app_settings_service.get_wechat_component_state(session)
        now = datetime.utcnow()
        if state["component_access_token"] and state["component_access_token_expires_at"]:
            if state["component_access_token_expires_at"] > now:
                return state["component_access_token"]
        refreshed = self.refresh_component_access_token(session)
        return refreshed["component_access_token"]

    def fetch_pre_auth_code(self, component_access_token: str) -> dict:
        request = self.build_pre_auth_code_request()
        url = request["url"].replace("<component_access_token>", component_access_token)
        return self._post_json(url, request["body"])

    def ensure_pre_auth_code(self, session: Session) -> dict:
        state = app_settings_service.get_wechat_component_state(session)
        now = datetime.utcnow()
        if state["pre_auth_code"] and state["pre_auth_code_expires_at"]:
            if state["pre_auth_code_expires_at"] > now:
                return {
                    "pre_auth_code": state["pre_auth_code"],
                    "expires_at": state["pre_auth_code_expires_at"].isoformat(),
                    "cached": True,
                }
        component_access_token = self.get_valid_component_access_token(session)
        payload = self.fetch_pre_auth_code(component_access_token)
        pre_auth_code = payload.get("pre_auth_code", "")
        expires_in = int(payload.get("expires_in", 600))
        expires_at = datetime.utcnow() + timedelta(seconds=max(expires_in - 60, 60))
        app_settings_service.set(session, app_settings_service.WECHAT_PRE_AUTH_CODE_KEY, pre_auth_code)
        app_settings_service.set_datetime(
            session,
            app_settings_service.WECHAT_PRE_AUTH_CODE_EXPIRES_AT_KEY,
            expires_at,
        )
        return {
            "pre_auth_code": pre_auth_code,
            "expires_at": expires_at.isoformat(),
            "cached": False,
            "raw_response": payload,
        }

    def parse_component_callback_xml(self, raw_xml: str) -> dict:
        root = ET.fromstring(raw_xml)
        parsed = {child.tag: (child.text or "") for child in root}
        return {
            "info_type": parsed.get("InfoType", ""),
            "component_verify_ticket": parsed.get("ComponentVerifyTicket", ""),
            "authorizer_appid": parsed.get("AuthorizerAppid", ""),
            "create_time": parsed.get("CreateTime", ""),
            "raw": parsed,
        }

    def store_component_callback_event(self, session: Session, raw_xml: str) -> dict:
        parsed = self.parse_component_callback_xml(raw_xml)
        app_settings_service.set(
            session,
            app_settings_service.WECHAT_LAST_CALLBACK_INFO_TYPE_KEY,
            parsed["info_type"],
        )
        app_settings_service.set_datetime(
            session,
            app_settings_service.WECHAT_LAST_CALLBACK_AT_KEY,
            datetime.utcnow(),
        )
        app_settings_service.set(
            session,
            app_settings_service.WECHAT_LAST_CALLBACK_RAW_XML_KEY,
            raw_xml,
        )
        if parsed["component_verify_ticket"]:
            app_settings_service.set(
                session,
                app_settings_service.WECHAT_COMPONENT_TICKET_KEY,
                parsed["component_verify_ticket"],
            )
        return {
            "stored": True,
            "parsed": parsed,
            "component_state": self.component_state(session),
        }

    def query_authorization(self, component_access_token: str, auth_code: str) -> dict:
        request = self.build_query_auth_request(auth_code)
        url = request["url"].replace("<component_access_token>", component_access_token)
        return self._post_json(url, request["body"])

    def exchange_callback_live(self, session: Session, auth_code: str) -> dict:
        component_access_token = self.get_valid_component_access_token(session)
        payload = self.query_authorization(component_access_token, auth_code)
        auth_info = payload.get("authorization_info", {})
        authorizer_app_id = auth_info.get("authorizer_appid", "")
        authorizer_access_token = auth_info.get("authorizer_access_token", "")
        authorizer_refresh_token = auth_info.get("authorizer_refresh_token", "")
        expires_in = int(auth_info.get("expires_in", 7200))
        expires_at = datetime.utcnow() + timedelta(seconds=max(expires_in - 300, 60))
        return {
            "authorizer_app_id": authorizer_app_id,
            "authorizer_access_token": authorizer_access_token,
            "authorizer_refresh_token": authorizer_refresh_token,
            "expires_at": expires_at.isoformat(),
            "account_profile": {
                "display_name": authorizer_app_id or "WeChat Official Account",
                "principal_name": "Authorized by third-party platform",
            },
            "raw_payload": payload,
        }

    def refresh_authorizer_token_live(
        self,
        component_access_token: str,
        authorizer_appid: str,
        authorizer_refresh_token: str,
    ) -> dict:
        request = self.build_authorizer_token_refresh_request(
            authorizer_appid=authorizer_appid,
            authorizer_refresh_token=authorizer_refresh_token,
        )
        url = request["url"].replace("<component_access_token>", component_access_token)
        return self._post_json(url, request["body"])

    def exchange_callback(self, auth_code: str) -> dict:
        now = datetime.utcnow()
        return {
            "authorizer_app_id": f"wx_{auth_code[-8:]}",
            "authorizer_access_token": "mock-access-token",
            "authorizer_refresh_token": "mock-refresh-token",
            "expires_at": (now + timedelta(hours=2)).isoformat(),
            "account_profile": {
                "display_name": "Demo Official Account",
                "principal_name": "Demo Studio",
            },
        }

    def refresh_authorization(self, _: str) -> dict:
        return {
            "authorizer_access_token": "mock-access-token-refreshed",
            "expires_at": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
        }

    def refresh_authorization_live(
        self,
        session: Session,
        *,
        authorizer_appid: str,
        authorizer_refresh_token: str,
    ) -> dict:
        component_access_token = self.get_valid_component_access_token(session)
        payload = self.refresh_authorizer_token_live(
            component_access_token,
            authorizer_appid=authorizer_appid,
            authorizer_refresh_token=authorizer_refresh_token,
        )
        expires_in = int(payload.get("expires_in", 7200))
        expires_at = datetime.utcnow() + timedelta(seconds=max(expires_in - 300, 60))
        return {
            "authorizer_access_token": payload.get("authorizer_access_token", ""),
            "authorizer_refresh_token": payload.get("authorizer_refresh_token", authorizer_refresh_token),
            "expires_at": expires_at.isoformat(),
            "raw_payload": payload,
        }

    def normalize_draft_payload(self, payload: dict) -> dict:
        article_payload = payload.get("article", {})
        content = article_payload.get("body", "")
        publish_notes = article_payload.get("publish_notes", [])
        if publish_notes:
            notes = "\n".join(f"- {item}" for item in publish_notes)
            content = f"{content}\n\n发布备注\n{notes}"
        article = {
            "title": article_payload.get("title", "Untitled"),
            "author": article_payload.get("author", "LinJian"),
            "digest": article_payload.get("summary", ""),
            "content": content,
            "content_source_url": article_payload.get("content_source_url", ""),
            "thumb_media_id": payload.get("cover_media_id", "cover_mock"),
            "need_open_comment": 0,
            "only_fans_can_comment": 0,
        }
        return {"articles": [article]}

    def build_draft_request_preview(self, authorizer_access_token: str, payload: dict) -> dict:
        blueprint = deepcopy(self.endpoint_blueprint()["add_draft"])
        blueprint["url"] = blueprint["url"].replace("<authorizer_access_token>", authorizer_access_token)
        blueprint["body"] = self.normalize_draft_payload(payload)
        return blueprint

    def build_upload_image_requests(
        self,
        authorizer_access_token: str,
        *,
        cover_local_path: str,
        content_local_paths: list[str],
    ) -> list[dict]:
        requests: list[dict] = []
        if cover_local_path:
            cover = deepcopy(self.endpoint_blueprint()["upload_image_for_article"])
            cover["url"] = cover["url"].replace("<authorizer_access_token>", authorizer_access_token)
            cover["body"] = {
                "media": Path(cover_local_path).name,
                "local_path": cover_local_path,
                "asset_role": "cover",
            }
            requests.append(cover)
        for index, local_path in enumerate(content_local_paths, start=1):
            item = deepcopy(self.endpoint_blueprint()["upload_image_for_article"])
            item["url"] = item["url"].replace("<authorizer_access_token>", authorizer_access_token)
            item["body"] = {
                "media": Path(local_path).name,
                "local_path": local_path,
                "asset_role": "content",
                "sequence": index,
            }
            requests.append(item)
        return requests

    def build_upload_thumb_request(
        self,
        authorizer_access_token: str,
        *,
        cover_local_path: str,
    ) -> dict:
        request = deepcopy(self.endpoint_blueprint()["upload_thumb_media"])
        request["url"] = request["url"].replace("<authorizer_access_token>", authorizer_access_token)
        request["body"] = {
            "media": Path(cover_local_path).name if cover_local_path else "",
            "local_path": cover_local_path,
            "asset_role": "thumb",
        }
        return request

    def build_publish_bundle(self, authorizer_access_token: str, payload: dict) -> dict:
        return {
            "thumb_request": self.build_upload_thumb_request(
                authorizer_access_token,
                cover_local_path=payload.get("cover_local_path", ""),
            ),
            "upload_requests": self.build_upload_image_requests(
                authorizer_access_token,
                cover_local_path=payload.get("cover_local_path", ""),
                content_local_paths=payload.get("content_local_paths", []),
            ),
            "draft_request": self.build_draft_request_preview(authorizer_access_token, payload),
        }

    def upload_thumb_media(self, authorizer_access_token: str, local_path: str) -> dict:
        url = self.endpoint_blueprint()["upload_thumb_media"]["url"].replace(
            "<authorizer_access_token>", authorizer_access_token
        )
        with httpx.Client(timeout=30) as client, open(local_path, "rb") as media_file:
            response = client.post(url, files={"media": (Path(local_path).name, media_file)})
            response.raise_for_status()
            return response.json()

    def upload_image_for_article(self, authorizer_access_token: str, local_path: str) -> dict:
        url = self.endpoint_blueprint()["upload_image_for_article"]["url"].replace(
            "<authorizer_access_token>", authorizer_access_token
        )
        with httpx.Client(timeout=30) as client, open(local_path, "rb") as media_file:
            response = client.post(url, files={"media": (Path(local_path).name, media_file)})
            response.raise_for_status()
            return response.json()

    def submit_draft(self, authorizer_access_token: str, payload: dict) -> dict:
        request = self.build_draft_request_preview(authorizer_access_token, payload)
        return self._post_json(request["url"], request["body"])

    def create_draft(
        self,
        account_id: int,
        payload: dict,
        *,
        authorizer_access_token: str = "mock-authorizer-access-token",
        authorization_mode: str = "mock",
    ) -> dict:
        normalized = self.normalize_draft_payload(payload)
        content_media_ids = payload.get("content_media_ids") or ["content_mock_1", "content_mock_2"]
        bundle = self.build_publish_bundle(authorizer_access_token, payload)
        return {
            "account_id": account_id,
            "draft_id": f"draft_{account_id}_{int(datetime.utcnow().timestamp())}",
            "cover_media_id": payload.get("cover_media_id", "cover_mock"),
            "content_media_ids": content_media_ids,
            "authorization_mode": authorization_mode,
            "upload_requests": bundle["upload_requests"],
            "draft_request": bundle["draft_request"],
            "payload": payload,
            "normalized_request": normalized,
        }

    def build_component_binding_guide(self, tenant_id: int) -> dict:
        status = self.config_status()
        return {
            "tenant_id": tenant_id,
            "mode": "third-party-platform",
            "ready_for_real_auth": status["ready_for_real_auth"],
            "callback_url": (
                f"{settings.wechat_callback_base_url.rstrip('/')}"
                f"/api/accounts/wechat/auth/callback?tenant_id={tenant_id}"
            ),
            "notes": [
                "后台用户先登录系统，再发起公众号授权。",
                "真实接入需要填写第三方平台 component 配置。",
                "当前仓库在未提供真实凭据时会退回 mock 授权链路。",
            ],
            "endpoints": self.endpoint_blueprint(),
        }


wechat_integration = WeChatIntegration()
