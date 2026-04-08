import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from app.core.config import settings
from app.db.session import get_session
from app.models.entities import ArticleJob, JobStep, MediaAsset, PublishRecord, WeChatAuthorization
from app.schemas.common import JobReplayPayload, PublishExecutePayload, TravelRequest
from app.services.app_settings import app_settings_service
from app.services.image_pipeline import image_pipeline_service
from app.services.secrets import secrets_service
from app.services.scheduler import scheduler_service
from app.services.workflow import workflow_service

router = APIRouter()

WORKFLOW_STEPS = [
    "researcher",
    "writer",
    "fact_checker",
    "formatter",
    "editor",
    "image_editor",
    "publisher",
]


def _utc_now() -> datetime:
    return datetime.utcnow()


def _duration_seconds(start: datetime | None, end: datetime | None) -> int:
    if not start or not end:
        return 0
    return max(0, int((end - start).total_seconds()))


def _job_timing_payload(
    job: ArticleJob,
    steps: list[JobStep],
    publish: PublishRecord | None = None,
) -> dict:
    last_step = steps[-1] if steps else None
    started_at = job.created_at
    latest_event_at = max(
        [item for item in [job.created_at, last_step.created_at if last_step else None, publish.created_at if publish else None] if item],
        default=job.created_at,
    )
    finished = job.status in {"succeeded", "failed"}
    finished_at = latest_event_at if finished else None
    elapsed_until = finished_at or _utc_now()
    current_step = ""
    current_step_status = ""
    next_step = ""
    if job.status == "pending":
        next_step = WORKFLOW_STEPS[0]
    elif job.status == "running":
        if last_step and last_step.status == "failed":
            current_step = last_step.agent_name
            current_step_status = "failed"
        elif last_step:
            current_index = WORKFLOW_STEPS.index(last_step.agent_name) if last_step.agent_name in WORKFLOW_STEPS else -1
            if current_index >= 0 and current_index + 1 < len(WORKFLOW_STEPS):
                current_step = WORKFLOW_STEPS[current_index + 1]
                current_step_status = "running"
                next_step = WORKFLOW_STEPS[current_index + 2] if current_index + 2 < len(WORKFLOW_STEPS) else ""
            else:
                current_step = last_step.agent_name or WORKFLOW_STEPS[-1]
                current_step_status = "running"
        else:
            current_step = WORKFLOW_STEPS[0]
            current_step_status = "running"
            next_step = WORKFLOW_STEPS[1]
    elif job.status == "succeeded":
        current_step = WORKFLOW_STEPS[-1] if steps else ""
        current_step_status = "succeeded"
    elif job.status == "failed":
        current_step = last_step.agent_name if last_step else ""
        current_step_status = last_step.status if last_step else "failed"

    return {
        "started_at": started_at.isoformat() if started_at else "",
        "last_event_at": latest_event_at.isoformat() if latest_event_at else "",
        "finished_at": finished_at.isoformat() if finished_at else "",
        "running_seconds": _duration_seconds(started_at, elapsed_until),
        "completed_seconds": _duration_seconds(started_at, finished_at) if finished_at else None,
        "current_step": current_step,
        "current_step_status": current_step_status,
        "next_step": next_step,
        "completed_step_count": len([step for step in steps if step.status == "succeeded"]),
        "total_step_count": len(WORKFLOW_STEPS),
    }


@router.get("")
def list_jobs(session: Session = Depends(get_session)):
    statement = select(ArticleJob).order_by(ArticleJob.id.desc())
    jobs = session.exec(statement).all()
    payload: list[dict] = []
    for job in jobs:
        steps = session.exec(
            select(JobStep).where(JobStep.article_job_id == (job.id or 0)).order_by(JobStep.id.asc())
        ).all()
        publish = session.exec(
            select(PublishRecord).where(PublishRecord.article_job_id == (job.id or 0))
        ).first()
        payload.append(
            {
                **job.model_dump(),
                "timing": _job_timing_payload(job, steps, publish),
            }
        )
    return payload


@router.post("/travel/generate-and-publish")
def generate_and_publish(payload: TravelRequest, session: Session = Depends(get_session)):
    job = workflow_service.create_job(session, payload)
    workflow_service.submit_job_by_id(job.id or 0)
    session.refresh(job)
    return job


def _media_url(request: Request, local_path: str) -> str:
    if not local_path:
        return ""
    try:
        relative = Path(local_path).resolve().relative_to(settings.media_path)
    except ValueError:
        return ""
    return f"{str(request.base_url).rstrip('/')}/media/{relative.as_posix()}"


def _image_source_summary(media_assets: list[MediaAsset]) -> dict:
    providers: set[str] = set()
    tags: set[str] = set()
    source_pages: set[str] = set()
    for asset in media_assets:
        metadata = json.loads(asset.metadata_json or "{}")
        provider = metadata.get("provider")
        tag = metadata.get("tag")
        source_page = metadata.get("source_page")
        if provider:
            providers.add(str(provider))
        if tag:
            tags.add(str(tag))
        if source_page:
            source_pages.add(str(source_page))
    return {
        "providers": sorted(providers),
        "tags": sorted(tags),
        "source_pages": sorted(source_pages),
        "asset_count": len(media_assets),
    }


def _serialize_publish_record(publish: PublishRecord | None) -> dict | None:
    if not publish:
        return None
    return {
        **publish.model_dump(),
        "thumb_result": json.loads(publish.thumb_result_json or "{}"),
        "upload_results": json.loads(publish.upload_results_json or "[]"),
        "draft_response": json.loads(publish.draft_response_json or "{}"),
        "content_media_ids_parsed": json.loads(publish.content_media_ids or "[]"),
    }


def _extract_publish_result(
    publish_record: dict | None,
    parsed_output: dict,
) -> dict:
    if publish_record and publish_record.get("raw_response"):
        try:
            return json.loads(publish_record["raw_response"])
        except (TypeError, json.JSONDecodeError):
            pass
    return parsed_output.get("publisher", {}).get("result", {}).get("publish_response", {}) or {}


def _build_publish_preview_payload(
    *,
    job: ArticleJob,
    parsed_output: dict,
    auth: WeChatAuthorization | None,
) -> dict:
    publish_preview = workflow_service.build_publish_preview(
        official_account_id=job.official_account_id,
        publish_payload=workflow_service._build_publish_payload(parsed_output),
        auth=auth,
        publish_readiness={
            "publish_ready": parsed_output.get("publisher", {}).get("result", {}).get("publish_ready"),
            "missing_assets": parsed_output.get("publisher", {}).get("result", {}).get("missing_assets", []),
            "dry_run_recommended": parsed_output.get("publisher", {}).get("result", {}).get(
                "dry_run_recommended"
            ),
            "authorization_mode_hint": parsed_output.get("publisher", {}).get("result", {}).get(
                "authorization_mode_hint"
            ),
            "required_actions": parsed_output.get("publisher", {}).get("result", {}).get(
                "required_actions", []
            ),
        },
    )
    return {
        "job_id": job.id,
        **publish_preview,
    }


@router.get("/{job_id}")
def get_job(job_id: int, request: Request, session: Session = Depends(get_session)):
    job = session.get(ArticleJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    steps = session.exec(
        select(JobStep).where(JobStep.article_job_id == job_id).order_by(JobStep.id.asc())
    ).all()
    publish = session.exec(
        select(PublishRecord).where(PublishRecord.article_job_id == job_id)
    ).first()
    auth = session.exec(
        select(WeChatAuthorization).where(WeChatAuthorization.official_account_id == job.official_account_id)
    ).first()
    media_assets = session.exec(
        select(MediaAsset).where(MediaAsset.article_job_id == job_id).order_by(MediaAsset.id.asc())
    ).all()
    parsed_output = json.loads(job.output_json or "{}")
    publish_record = _serialize_publish_record(publish)
    return {
        "job": job,
        "timing": _job_timing_payload(job, steps, publish),
        "steps": steps,
        "publish_record": publish_record,
        "publish_result": _extract_publish_result(publish_record, parsed_output),
        "publish_preview": _build_publish_preview_payload(job=job, parsed_output=parsed_output, auth=auth),
        "media_assets": [
            {
                **asset.model_dump(),
                "metadata": json.loads(asset.metadata_json or "{}"),
                "upload_response": json.loads(asset.upload_response_json or "{}"),
                "media_url": _media_url(request, asset.local_path),
            }
            for asset in media_assets
        ],
        "image_source_summary": _image_source_summary(media_assets),
        "parsed_output": parsed_output,
    }


@router.post("/{job_id}/replay")
def replay_job(job_id: int, _: JobReplayPayload | None = None):
    replay = scheduler_service.replay_job(job_id)
    if not replay:
        raise HTTPException(status_code=404, detail="Job not found")
    parsed_output = json.loads(replay.output_json or "{}")
    return {
        "ok": True,
        "mode": "replay",
        "job": replay,
        "publish_record": None,
        "publish_result": parsed_output.get("publisher", {}).get("result", {}).get("publish_response", {}) or {},
    }


@router.post("/{job_id}/refresh-images")
def refresh_job_images(job_id: int, session: Session = Depends(get_session)):
    job = session.get(ArticleJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    parsed_output = json.loads(job.output_json or "{}")
    image_editor = parsed_output.get("image_editor", {})
    editor = parsed_output.get("editor", {})
    formatter = parsed_output.get("formatter", {})

    image_pack = image_pipeline_service.rebuild_for_job(
        session=session,
        article_job_id=job.id or 0,
        official_account_id=job.official_account_id,
        destination=job.destination or parsed_output.get("destination", "待定目的地"),
        article_context={
            "title": editor.get("result", {}).get("final_title", ""),
            "summary": editor.get("result", {}).get("summary", ""),
        },
    )
    slot_plan = image_editor.get("result", {}).get("slot_plan", [])
    slot_assignments = workflow_service._assign_images_to_slots(slot_plan, image_pack.get("images", []))
    image_editor.setdefault("result", {})
    image_editor["result"]["image_asset_pack"] = image_pack
    image_editor["result"]["provider_context"] = {
        "provider": image_pack.get("provider", ""),
        "image_count": image_pack.get("image_count", 0),
        "raw_image_count": image_pack.get("raw_image_count", image_pack.get("image_count", 0)),
        "source_note_count": image_pack.get("note_count", 0),
    }
    image_editor["result"]["slot_assignments"] = slot_assignments
    parsed_output["image_editor"] = image_editor

    if "publisher" in parsed_output:
        parsed_output["publisher"].setdefault("result", {})
        auth = session.exec(
            select(WeChatAuthorization).where(WeChatAuthorization.official_account_id == job.official_account_id)
        ).first()
        publish_preview = _build_publish_preview_payload(job=job, parsed_output=parsed_output, auth=auth)
        parsed_output["publisher"]["result"]["publish_preview"] = publish_preview

    job.output_json = json.dumps(parsed_output, ensure_ascii=False)
    session.add(job)
    session.commit()
    auth = session.exec(
        select(WeChatAuthorization).where(WeChatAuthorization.official_account_id == job.official_account_id)
    ).first()
    return {
        "ok": True,
        "mode": "refresh_images",
        "job_id": job.id,
        "image_asset_pack": image_pack,
        "slot_assignments": slot_assignments,
        "image_slots": formatter.get("result", {}).get("image_slots", []),
        "publish_record": None,
        "publish_result": {},
        "publish_preview": _build_publish_preview_payload(job=job, parsed_output=parsed_output, auth=auth),
    }


@router.get("/{job_id}/publish-preview")
def get_publish_preview(job_id: int, session: Session = Depends(get_session)):
    job = session.get(ArticleJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    parsed_output = json.loads(job.output_json or "{}")
    auth = session.exec(
        select(WeChatAuthorization).where(WeChatAuthorization.official_account_id == job.official_account_id)
    ).first()
    return {
        "ok": True,
        "mode": "preview",
        "publish_record": None,
        "publish_result": {},
        "publish_preview": _build_publish_preview_payload(job=job, parsed_output=parsed_output, auth=auth),
    }


@router.post("/{job_id}/publish-execute")
def execute_publish(
    job_id: int,
    payload: PublishExecutePayload,
    session: Session = Depends(get_session),
):
    job = session.get(ArticleJob, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    parsed_output = json.loads(job.output_json or "{}")
    auth = session.exec(
        select(WeChatAuthorization).where(WeChatAuthorization.official_account_id == job.official_account_id)
    ).first()
    authorizer_access_token = (
        secrets_service.decrypt_if_needed(auth.authorizer_access_token)
        if auth and auth.authorizer_access_token
        else "mock-authorizer-access-token"
    )
    authorization_mode = workflow_service._authorization_mode(auth)
    publish_payload = workflow_service._build_publish_payload(parsed_output)

    if payload.dry_run or authorization_mode != "third_party_platform":
        return {
            "ok": True,
            "mode": "dry_run",
            "publish_record": None,
            "publish_result": {},
            **_build_publish_preview_payload(job=job, parsed_output=parsed_output, auth=auth),
        }

    publish_result = workflow_service._execute_publish(
        official_account_id=job.official_account_id,
        publish_payload=publish_payload,
        authorizer_access_token=authorizer_access_token,
        authorization_mode=authorization_mode,
    )
    workflow_service._sync_media_assets_after_publish(
        session=session,
        article_job_id=job.id or 0,
        publish_result=publish_result,
    )
    publish_record = PublishRecord(
        article_job_id=job.id,
        official_account_id=job.official_account_id,
        authorization_mode=publish_result.get("authorization_mode", authorization_mode),
        draft_id=publish_result.get("draft_id", ""),
        cover_media_id=publish_result.get("cover_media_id", ""),
        thumb_result_json=json.dumps(
            publish_result.get("thumb_result") or {},
            ensure_ascii=False,
        ),
        upload_results_json=json.dumps(
            publish_result.get("upload_results") or [],
            ensure_ascii=False,
        ),
        draft_response_json=json.dumps(
            publish_result.get("draft_response") or {},
            ensure_ascii=False,
        ),
        content_media_ids=json.dumps(publish_result.get("content_media_ids", []), ensure_ascii=False),
        raw_response=json.dumps(publish_result, ensure_ascii=False),
    )
    session.add(publish_record)
    session.commit()
    session.refresh(publish_record)
    publish_preview = workflow_service.build_publish_preview(
        official_account_id=job.official_account_id,
        publish_payload=publish_result.get("payload") or publish_payload,
        auth=auth,
        publish_readiness={
            "publish_ready": parsed_output.get("publisher", {}).get("result", {}).get("publish_ready"),
            "missing_assets": parsed_output.get("publisher", {}).get("result", {}).get("missing_assets", []),
            "dry_run_recommended": parsed_output.get("publisher", {}).get("result", {}).get(
                "dry_run_recommended"
            ),
            "authorization_mode_hint": parsed_output.get("publisher", {}).get("result", {}).get(
                "authorization_mode_hint"
            ),
            "required_actions": parsed_output.get("publisher", {}).get("result", {}).get(
                "required_actions", []
            ),
        },
        authorizer_access_token=authorizer_access_token,
    )
    return {
        "ok": True,
        "mode": "live",
        "authorization_mode": authorization_mode,
        "publish_preview": publish_preview,
        "publish_record": _serialize_publish_record(publish_record),
        "publish_result": publish_result,
    }
