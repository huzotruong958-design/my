from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from app.db.session import get_session

from app.integrations.search import search_service
from app.schemas.common import (
    ExternalImageManifestPayload,
    ImageProviderUpdatePayload,
    SearchPreviewPayload,
    XiaohongshuMcpConfigPayload,
    XiaohongshuPreviewPayload,
    XiaohongshuSeedUrlsPayload,
)
from app.integrations.xiaohongshu_mcp import XiaohongshuMcpClient
from app.services.app_settings import app_settings_service
from app.services.image_pipeline import image_pipeline_service

router = APIRouter()


@router.post("/preview")
def preview_search(payload: SearchPreviewPayload):
    return search_service.preview(payload.destination, payload.intent)


@router.get("/image-providers")
def list_image_providers(session: Session = Depends(get_session)):
    current = app_settings_service.get_image_provider(session)
    status = image_pipeline_service.provider_status(current)
    manifest = app_settings_service.get_external_image_manifest(session)
    xiaohongshu_seed_urls = app_settings_service.get_xiaohongshu_seed_urls(session)
    xiaohongshu_mcp_config = app_settings_service.get_xiaohongshu_mcp_config(session)
    return {
        **status,
        "manifest_count": len(manifest),
        "manifest_preview": manifest[:3],
        "xiaohongshu_seed_count": len(xiaohongshu_seed_urls),
        "xiaohongshu_seed_preview": xiaohongshu_seed_urls[:3],
        "xiaohongshu_mcp": {
            "enabled": xiaohongshu_mcp_config["enabled"],
            "endpoint": xiaohongshu_mcp_config["endpoint"],
            "auth_header": xiaohongshu_mcp_config["auth_header"],
            "configured": bool(xiaohongshu_mcp_config["endpoint"]),
            "api_token_masked": (
                f"{xiaohongshu_mcp_config['api_token'][:4]}...{xiaohongshu_mcp_config['api_token'][-4:]}"
                if xiaohongshu_mcp_config["api_token"] and len(xiaohongshu_mcp_config["api_token"]) > 8
                else ""
            ),
            "timeout_seconds": xiaohongshu_mcp_config["timeout_seconds"],
            "last_probe": xiaohongshu_mcp_config["last_probe"],
        },
    }


@router.patch("/image-providers")
def update_image_provider(
    payload: ImageProviderUpdatePayload,
    session: Session = Depends(get_session),
):
    if payload.provider not in image_pipeline_service.providers:
        raise HTTPException(status_code=400, detail="Unknown image provider")
    app_settings_service.set(
        session,
        app_settings_service.IMAGE_PROVIDER_KEY,
        payload.provider,
    )
    manifest = app_settings_service.get_external_image_manifest(session)
    xiaohongshu_seed_urls = app_settings_service.get_xiaohongshu_seed_urls(session)
    xiaohongshu_mcp_config = app_settings_service.get_xiaohongshu_mcp_config(session)
    return {
        **image_pipeline_service.provider_status(payload.provider),
        "manifest_count": len(manifest),
        "manifest_preview": manifest[:3],
        "xiaohongshu_seed_count": len(xiaohongshu_seed_urls),
        "xiaohongshu_seed_preview": xiaohongshu_seed_urls[:3],
        "xiaohongshu_mcp": {
            "enabled": xiaohongshu_mcp_config["enabled"],
            "endpoint": xiaohongshu_mcp_config["endpoint"],
            "auth_header": xiaohongshu_mcp_config["auth_header"],
            "configured": bool(xiaohongshu_mcp_config["endpoint"]),
            "api_token_masked": (
                f"{xiaohongshu_mcp_config['api_token'][:4]}...{xiaohongshu_mcp_config['api_token'][-4:]}"
                if xiaohongshu_mcp_config["api_token"] and len(xiaohongshu_mcp_config["api_token"]) > 8
                else ""
            ),
            "timeout_seconds": xiaohongshu_mcp_config["timeout_seconds"],
            "last_probe": xiaohongshu_mcp_config["last_probe"],
        },
    }


@router.get("/external-image-manifest")
def get_external_image_manifest(session: Session = Depends(get_session)):
    return {
        "items": app_settings_service.get_external_image_manifest(session),
    }


@router.put("/external-image-manifest")
def update_external_image_manifest(
    payload: ExternalImageManifestPayload,
    session: Session = Depends(get_session),
):
    normalized = [item.model_dump() for item in payload.items]
    app_settings_service.set_external_image_manifest(session, normalized)
    return {"items": normalized, "count": len(normalized)}


@router.get("/xiaohongshu-seed-urls")
def get_xiaohongshu_seed_urls(session: Session = Depends(get_session)):
    urls = app_settings_service.get_xiaohongshu_seed_urls(session)
    return {"urls": urls, "count": len(urls)}


@router.put("/xiaohongshu-seed-urls")
def update_xiaohongshu_seed_urls(
    payload: XiaohongshuSeedUrlsPayload,
    session: Session = Depends(get_session),
):
    normalized = [str(item).strip() for item in payload.urls if str(item).strip()]
    app_settings_service.set_xiaohongshu_seed_urls(session, normalized)
    return {"urls": normalized, "count": len(normalized)}


@router.post("/xiaohongshu-preview")
def preview_xiaohongshu(payload: XiaohongshuPreviewPayload, session: Session = Depends(get_session)):
    config = app_settings_service.get_xiaohongshu_mcp_config(session)
    article_context = {
        "title": payload.title or "",
        "summary": payload.summary or "",
    }
    if config["enabled"] and config["endpoint"]:
        return image_pipeline_service.preview_xiaohongshu_mcp(
            destination=payload.destination or "",
            article_context=article_context,
            limit=payload.limit,
            mcp_config=config,
        )
    urls = payload.urls or app_settings_service.get_xiaohongshu_seed_urls(session)
    return image_pipeline_service.preview_xiaohongshu_seed_urls(
        urls,
        destination=payload.destination or "",
        article_context=article_context,
        limit=payload.limit,
    )


@router.get("/xiaohongshu-mcp-config")
def get_xiaohongshu_mcp_config(session: Session = Depends(get_session)):
    config = app_settings_service.get_xiaohongshu_mcp_config(session)
    return {
        "enabled": config["enabled"],
        "endpoint": config["endpoint"],
        "auth_header": config["auth_header"],
        "api_token_masked": (
            f"{config['api_token'][:4]}...{config['api_token'][-4:]}"
            if config["api_token"] and len(config["api_token"]) > 8
            else ""
        ),
        "timeout_seconds": config["timeout_seconds"],
        "last_probe": config["last_probe"],
    }


@router.put("/xiaohongshu-mcp-config")
def update_xiaohongshu_mcp_config(
    payload: XiaohongshuMcpConfigPayload,
    session: Session = Depends(get_session),
):
    app_settings_service.set_xiaohongshu_mcp_config(
        session,
        enabled=payload.enabled,
        endpoint=payload.endpoint,
        api_token=payload.api_token,
        auth_header=payload.auth_header,
        timeout_seconds=payload.timeout_seconds,
    )
    return get_xiaohongshu_mcp_config(session)


@router.post("/xiaohongshu-mcp-probe")
def probe_xiaohongshu_mcp(session: Session = Depends(get_session)):
    config = app_settings_service.get_xiaohongshu_mcp_config(session)
    if not config["endpoint"]:
        raise HTTPException(status_code=400, detail="Xiaohongshu MCP endpoint is not configured")
    try:
        client = XiaohongshuMcpClient(
            endpoint=config["endpoint"],
            api_token=config["api_token"],
            timeout_seconds=config["timeout_seconds"],
            auth_header=config["auth_header"],
        )
        result = client.probe()
    except Exception as exc:
        result = {
            "ok": False,
            "endpoint": config["endpoint"],
            "error": str(exc),
        }
    app_settings_service.set_xiaohongshu_mcp_last_probe(session, result)
    return result
