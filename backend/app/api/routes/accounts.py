from datetime import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlmodel import Session, select

from app.db.session import get_session
from app.integrations.wechat import wechat_integration
from app.models.entities import OfficialAccount, WeChatAuthorization
from app.schemas.common import (
    AccountCreatePayload,
    ComponentCallbackMockPayload,
    ComponentTicketPayload,
)

router = APIRouter()


def serialize_authorization(auth: WeChatAuthorization | None) -> dict | None:
    if not auth:
        return None
    return {
        "id": auth.id,
        "authorizer_app_id": auth.authorizer_app_id,
        "expires_at": auth.expires_at,
        "updated_at": auth.updated_at,
        "has_refresh_token": bool(auth.authorizer_refresh_token),
    }


@router.get("")
def list_accounts(session: Session = Depends(get_session)):
    accounts = session.exec(select(OfficialAccount)).all()
    result = []
    for account in accounts:
        auth = session.exec(
            select(WeChatAuthorization).where(WeChatAuthorization.official_account_id == account.id)
        ).first()
        result.append(
            {
                "id": account.id,
                "tenant_id": account.tenant_id,
                "display_name": account.display_name,
                "wechat_app_id": account.wechat_app_id,
                "principal_name": account.principal_name,
                "status": account.status,
                "publishable": account.publishable,
                "last_refreshed_at": account.last_refreshed_at,
                "authorization": serialize_authorization(auth),
            }
        )
    return result


@router.post("")
def create_account(payload: AccountCreatePayload, session: Session = Depends(get_session)):
    account = OfficialAccount(
        tenant_id=payload.tenant_id,
        display_name=payload.display_name,
        wechat_app_id=payload.wechat_app_id,
        principal_name=payload.principal_name or "",
    )
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


@router.post("/wechat/auth/start")
def start_wechat_auth(tenant_id: int, session: Session = Depends(get_session)):
    pre_auth_code = None
    component_state = wechat_integration.component_state(session)
    if component_state["ready_for_real_auth"] and component_state["has_component_verify_ticket"]:
        try:
            pre_auth_code = wechat_integration.ensure_pre_auth_code(session)["pre_auth_code"]
        except Exception:
            pre_auth_code = None
    return {
        "authorization_url": wechat_integration.build_authorization_url(tenant_id, pre_auth_code),
        "binding_guide": wechat_integration.build_component_binding_guide(tenant_id),
    }


@router.get("/wechat/config-status")
def wechat_config_status(session: Session = Depends(get_session)):
    return wechat_integration.component_state(session)


@router.get("/wechat/diagnostics")
def wechat_diagnostics(session: Session = Depends(get_session)):
    return {
        "config": wechat_integration.component_state(session),
        "endpoints": wechat_integration.endpoint_blueprint(),
        "component_access_token_request": wechat_integration.build_component_access_token_request(),
        "pre_auth_code_request": wechat_integration.build_pre_auth_code_request(),
    }


@router.post("/wechat/component/callback/mock")
def mock_wechat_component_callback(
    payload: ComponentCallbackMockPayload,
    session: Session = Depends(get_session),
):
    authorizer = (
        f"<AuthorizerAppid>{payload.authorizer_appid}</AuthorizerAppid>"
        if payload.authorizer_appid
        else ""
    )
    raw_xml = (
        "<xml>"
        f"<InfoType>{payload.info_type}</InfoType>"
        f"<ComponentVerifyTicket>{payload.component_verify_ticket}</ComponentVerifyTicket>"
        f"{authorizer}"
        f"<CreateTime>{int(datetime.utcnow().timestamp())}</CreateTime>"
        "</xml>"
    )
    return wechat_integration.store_component_callback_event(session, raw_xml)


@router.get("/wechat/component/callback")
def wechat_component_callback_verify(echostr: str = ""):
    return Response(content=echostr, media_type="text/plain")


@router.post("/wechat/component/callback")
async def wechat_component_callback_receive(
    request: Request,
    session: Session = Depends(get_session),
):
    raw_xml = (await request.body()).decode("utf-8", errors="ignore")
    result = wechat_integration.store_component_callback_event(session, raw_xml)
    return {"success": True, **result}


@router.post("/wechat/component-ticket")
def save_component_ticket(
    payload: ComponentTicketPayload,
    session: Session = Depends(get_session),
):
    return wechat_integration.store_component_verify_ticket(session, payload.component_verify_ticket)


@router.post("/wechat/component-access-token/refresh")
def refresh_component_access_token(session: Session = Depends(get_session)):
    try:
        return wechat_integration.refresh_component_access_token(session)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/wechat/pre-auth-code/refresh")
def refresh_pre_auth_code(session: Session = Depends(get_session)):
    try:
        return wechat_integration.ensure_pre_auth_code(session)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{account_id}/publish-context")
def get_account_publish_context(account_id: int, session: Session = Depends(get_session)):
    account = session.get(OfficialAccount, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    auth = session.exec(
        select(WeChatAuthorization).where(WeChatAuthorization.official_account_id == account_id)
    ).first()
    authorization_mode = "missing"
    refresh_request = None
    if auth:
        raw_payload = auth.raw_payload or ""
        authorization_mode = (
            "mock"
            if "mock-authorize" in raw_payload or auth.authorizer_access_token.startswith("mock-")
            else "third_party_platform"
        )
        refresh_request = wechat_integration.build_authorizer_token_refresh_request(
            authorizer_appid=auth.authorizer_app_id,
            authorizer_refresh_token=auth.authorizer_refresh_token,
        )
    return {
        "account_id": account.id,
        "display_name": account.display_name,
        "publishable": account.publishable,
        "authorization_mode": authorization_mode,
        "authorization": serialize_authorization(auth),
        "refresh_request_preview": refresh_request,
    }


@router.get("/wechat/auth/callback")
def wechat_auth_callback(
    tenant_id: int,
    auth_code: str = "mock-auth-code",
    session: Session = Depends(get_session),
):
    component_state = wechat_integration.component_state(session)
    if component_state["ready_for_real_auth"] and component_state["component_access_token_valid"]:
        try:
            payload = wechat_integration.exchange_callback_live(session, auth_code)
        except Exception:
            payload = wechat_integration.exchange_callback(auth_code)
    else:
        payload = wechat_integration.exchange_callback(auth_code)

    account = session.exec(
        select(OfficialAccount).where(
            OfficialAccount.tenant_id == tenant_id,
            OfficialAccount.wechat_app_id == payload["authorizer_app_id"],
        )
    ).first()
    if not account:
        account = OfficialAccount(
            tenant_id=tenant_id,
            wechat_app_id=payload["authorizer_app_id"],
        )
    account.display_name = payload["account_profile"]["display_name"]
    account.principal_name = payload["account_profile"]["principal_name"]
    account.status = "publishable"
    account.publishable = True
    account.last_refreshed_at = datetime.utcnow()
    session.add(account)
    session.commit()
    session.refresh(account)

    auth = session.exec(
        select(WeChatAuthorization).where(WeChatAuthorization.official_account_id == account.id)
    ).first()
    if not auth:
        auth = WeChatAuthorization(
            official_account_id=account.id,
            authorizer_app_id=payload["authorizer_app_id"],
            authorizer_access_token=payload["authorizer_access_token"],
            authorizer_refresh_token=payload["authorizer_refresh_token"],
            expires_at=datetime.fromisoformat(payload["expires_at"]),
            raw_payload=json.dumps(payload, ensure_ascii=False),
        )
    else:
        auth.authorizer_app_id = payload["authorizer_app_id"]
        auth.authorizer_access_token = payload["authorizer_access_token"]
        auth.authorizer_refresh_token = payload["authorizer_refresh_token"]
        auth.expires_at = datetime.fromisoformat(payload["expires_at"])
        auth.raw_payload = json.dumps(payload, ensure_ascii=False)
        auth.updated_at = datetime.utcnow()
    session.add(auth)
    session.commit()
    return {"account": account, "authorization": auth}


@router.post("/{account_id}/refresh-status")
def refresh_account_status(account_id: int, session: Session = Depends(get_session)):
    account = session.get(OfficialAccount, account_id)
    auth = session.exec(
        select(WeChatAuthorization).where(WeChatAuthorization.official_account_id == account_id)
    ).first()
    if not account or not auth:
        return {"ok": False, "message": "Account authorization not found"}
    raw_payload = auth.raw_payload or ""
    if "mock-authorize" in raw_payload or auth.authorizer_access_token.startswith("mock-"):
        refreshed = wechat_integration.refresh_authorization(auth.authorizer_refresh_token)
    else:
        refreshed = wechat_integration.refresh_authorization_live(
            session,
            authorizer_appid=auth.authorizer_app_id,
            authorizer_refresh_token=auth.authorizer_refresh_token,
        )
    auth.authorizer_access_token = refreshed["authorizer_access_token"]
    if refreshed.get("authorizer_refresh_token"):
        auth.authorizer_refresh_token = refreshed["authorizer_refresh_token"]
    auth.expires_at = datetime.fromisoformat(refreshed["expires_at"])
    auth.updated_at = datetime.utcnow()
    account.publishable = True
    account.status = "publishable"
    account.last_refreshed_at = datetime.utcnow()
    session.add(auth)
    session.add(account)
    session.commit()
    return {"ok": True, "account": account}


@router.post("/{account_id}/mock-authorize")
def mock_authorize_account(account_id: int, session: Session = Depends(get_session)):
    account = session.get(OfficialAccount, account_id)
    if not account:
        return {"ok": False, "message": "Account not found"}

    auth = session.exec(
        select(WeChatAuthorization).where(WeChatAuthorization.official_account_id == account_id)
    ).first()
    if not auth:
        auth = WeChatAuthorization(
            official_account_id=account_id,
            authorizer_app_id=account.wechat_app_id,
            authorizer_access_token="mock-access-token",
            authorizer_refresh_token="mock-refresh-token",
            expires_at=datetime.utcnow(),
            raw_payload=json.dumps({"source": "mock-authorize"}),
        )

    account.publishable = True
    account.status = "publishable"
    account.last_refreshed_at = datetime.utcnow()
    auth.updated_at = datetime.utcnow()

    session.add(account)
    session.add(auth)
    session.commit()
    session.refresh(account)
    return {"ok": True, "account": account}
