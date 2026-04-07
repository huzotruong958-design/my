from __future__ import annotations

import json
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from sqlmodel import Session, select

from app.agents.prompts import AGENT_PROMPTS
from app.integrations.search import search_service
from app.integrations.wechat import wechat_integration
from app.models.entities import (
    ArticleJob,
    JobStatus,
    JobStep,
    MediaAsset,
    OfficialAccount,
    PublishRecord,
    WeChatAuthorization,
)
from app.schemas.common import TravelRequest
from app.services.app_settings import app_settings_service
from app.services.image_pipeline import image_pipeline_service
from app.services.llm_runtime import llm_runtime
from app.services.model_router import model_router


class WorkflowState(TypedDict, total=False):
    job_id: int
    tenant_id: int
    account_id: int
    account_name: str
    start_date: str
    end_date: str
    destination: str
    season_theme: str
    search_preview: dict
    researcher: dict
    fact_checker: dict
    writer: dict
    formatter: dict
    editor: dict
    image_editor: dict
    publisher: dict


class WorkflowService:
    steps = [
        "researcher",
        "writer",
        "fact_checker",
        "formatter",
        "editor",
        "image_editor",
        "publisher",
    ]

    def create_job(self, session: Session, payload: TravelRequest) -> ArticleJob:
        job = ArticleJob(
            tenant_id=payload.tenant_id,
            official_account_id=payload.account_id,
            start_date=payload.start_date,
            end_date=payload.end_date,
            status=JobStatus.pending,
            payload_json=payload.model_dump_json(),
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        return job

    def probe_agent(self, session: Session, tenant_id: int, agent_type: str, state: dict) -> dict:
        model_info = model_router.resolve(session, tenant_id, agent_type)
        return self._execute_agent(agent_type, state, model_info)

    def run_job(self, session: Session, job: ArticleJob) -> ArticleJob:
        account = session.get(OfficialAccount, job.official_account_id)
        if not account:
            job.status = JobStatus.failed
            job.error_message = "Official account not found."
            session.add(job)
            session.commit()
            return job

        job.status = JobStatus.running
        session.add(job)
        session.commit()

        initial_state: WorkflowState = {
            "job_id": job.id or 0,
            "tenant_id": job.tenant_id,
            "account_id": job.official_account_id,
            "account_name": account.display_name,
            "start_date": job.start_date,
            "end_date": job.end_date,
            "destination": "待定目的地",
            "season_theme": self._season_theme(job.start_date),
            "search_preview": search_service.preview("待定目的地", "destination_overview"),
        }

        graph = self._build_graph(session, job)
        final_state = graph.invoke(initial_state)

        job.destination = final_state["destination"]
        job.status = JobStatus.succeeded
        job.output_json = json.dumps(final_state, ensure_ascii=False)
        session.add(job)
        session.commit()
        session.refresh(job)
        return job

    def _build_graph(self, session: Session, job: ArticleJob):
        graph = StateGraph(WorkflowState)

        for step_name in self.steps:
            graph.add_node(step_name, self._make_node(step_name, session, job))

        graph.add_edge(START, self.steps[0])
        for current_step, next_step in zip(self.steps, self.steps[1:]):
            graph.add_edge(current_step, next_step)
        graph.add_edge(self.steps[-1], END)
        return graph.compile()

    def _make_node(self, step_name: str, session: Session, job: ArticleJob):
        def node(state: WorkflowState) -> WorkflowState:
            model_info = model_router.resolve(session, job.tenant_id, step_name)
            output = self._execute_agent(step_name, state, model_info)

            updated: WorkflowState = {step_name: output}
            if step_name == "researcher":
                updated["destination"] = output["result"]["destination"]
            if step_name == "image_editor":
                image_pack = image_pipeline_service.collect_for_job(
                    session=session,
                    article_job_id=job.id or 0,
                    official_account_id=job.official_account_id,
                    destination=state.get("destination", "待定目的地"),
                    article_context={
                        "title": state.get("editor", {}).get("result", {}).get("final_title", ""),
                        "summary": state.get("editor", {}).get("result", {}).get("summary", ""),
                    },
                )
                output["result"]["image_asset_pack"] = image_pack
                output["result"]["provider_context"] = {
                    "provider": image_pack.get("provider", ""),
                    "manifest_count": len(app_settings_service.get_external_image_manifest(session)),
                }
                slot_plan = output["result"].get("slot_plan", [])
                images = image_pack.get("images", []) if isinstance(image_pack, dict) else []
                output["result"]["slot_assignments"] = self._assign_images_to_slots(slot_plan, images)
            if step_name == "publisher":
                auth = session.exec(
                    select(WeChatAuthorization).where(
                        WeChatAuthorization.official_account_id == job.official_account_id
                    )
                ).first()
                authorizer_access_token = (
                    auth.authorizer_access_token if auth and auth.authorizer_access_token else "mock-authorizer-access-token"
                )
                publish_payload = self._build_publish_payload(state)
                publish_preview = self.build_publish_preview(
                    official_account_id=job.official_account_id,
                    publish_payload=publish_payload,
                    auth=auth,
                    publish_readiness={
                        "publish_ready": output["result"].get("publish_ready"),
                        "missing_assets": output["result"].get("missing_assets", []),
                        "dry_run_recommended": output["result"].get("dry_run_recommended"),
                        "authorization_mode_hint": output["result"].get("authorization_mode_hint"),
                        "required_actions": output["result"].get("required_actions", []),
                    },
                    authorizer_access_token=authorizer_access_token,
                )
                output["result"]["publish_preview"] = publish_preview
                publish = self._execute_publish(
                    official_account_id=job.official_account_id,
                    publish_payload=publish_payload,
                    authorizer_access_token=authorizer_access_token,
                    authorization_mode=publish_preview["authorization_mode"],
                )
                self._sync_media_assets_after_publish(
                    session=session,
                    article_job_id=job.id or 0,
                    publish_result=publish,
                )
                output["result"]["publish_response"] = publish
                session.add(
                    PublishRecord(
                        article_job_id=job.id,
                        official_account_id=job.official_account_id,
                        authorization_mode=publish.get("authorization_mode", authorization_mode),
                        draft_id=publish["draft_id"],
                        cover_media_id=publish["cover_media_id"],
                        thumb_result_json=json.dumps(
                            publish.get("thumb_result") or {},
                            ensure_ascii=False,
                        ),
                        upload_results_json=json.dumps(
                            publish.get("upload_results") or [],
                            ensure_ascii=False,
                        ),
                        draft_response_json=json.dumps(
                            publish.get("draft_response") or {},
                            ensure_ascii=False,
                        ),
                        content_media_ids=json.dumps(publish["content_media_ids"]),
                        raw_response=json.dumps(publish, ensure_ascii=False),
                    )
                )
            session.add(
                JobStep(
                    article_job_id=job.id,
                    agent_name=step_name,
                    status="succeeded",
                    model_provider=model_info["provider"],
                    model_name=model_info["model_name"],
                    output_json=json.dumps(output, ensure_ascii=False),
                )
            )
            session.commit()
            return updated

        return node

    def build_authorization_context(self, auth: WeChatAuthorization | None) -> dict:
        authorization_mode = self._authorization_mode(auth)
        return {
            "has_authorization": bool(auth),
            "authorization_mode": authorization_mode,
            "authorizer_app_id": auth.authorizer_app_id if auth else "",
            "expires_at": auth.expires_at.isoformat() if auth and auth.expires_at else "",
        }

    def build_publish_preview(
        self,
        *,
        official_account_id: int,
        publish_payload: dict,
        auth: WeChatAuthorization | None,
        publish_readiness: dict | None = None,
        authorizer_access_token: str | None = None,
    ) -> dict:
        authorization_context = self.build_authorization_context(auth)
        access_token = authorizer_access_token or (
            auth.authorizer_access_token if auth and auth.authorizer_access_token else "mock-authorizer-access-token"
        )
        publish_bundle = wechat_integration.build_publish_bundle(access_token, publish_payload)
        return {
            "official_account_id": official_account_id,
            "authorization_mode": authorization_context["authorization_mode"],
            "authorization_context": authorization_context,
            "publish_payload": publish_payload,
            "publish_bundle": publish_bundle,
            "publish_readiness": {
                "publish_ready": (publish_readiness or {}).get("publish_ready"),
                "missing_assets": (publish_readiness or {}).get("missing_assets", []),
                "dry_run_recommended": (publish_readiness or {}).get("dry_run_recommended"),
                "authorization_mode_hint": (publish_readiness or {}).get("authorization_mode_hint"),
                "required_actions": (publish_readiness or {}).get("required_actions", []),
            },
        }

    def _execute_publish(
        self,
        *,
        official_account_id: int,
        publish_payload: dict,
        authorizer_access_token: str,
        authorization_mode: str,
    ) -> dict:
        if authorization_mode != "third_party_platform":
            return wechat_integration.create_draft(
                official_account_id,
                publish_payload,
                authorizer_access_token=authorizer_access_token,
                authorization_mode=authorization_mode,
            )

        live_payload = dict(publish_payload)
        thumb_result = None
        cover_local_path = live_payload.get("cover_local_path", "")
        if cover_local_path:
            thumb_result = wechat_integration.upload_thumb_media(authorizer_access_token, cover_local_path)
            if thumb_result.get("media_id"):
                live_payload["cover_media_id"] = thumb_result["media_id"]

        upload_results = []
        for local_path in live_payload.get("content_local_paths", []):
            upload_results.append(
                wechat_integration.upload_image_for_article(authorizer_access_token, local_path)
            )

        draft_response = wechat_integration.submit_draft(authorizer_access_token, live_payload)
        return {
            "account_id": official_account_id,
            "draft_id": str(draft_response.get("media_id") or draft_response.get("draft_id") or ""),
            "cover_media_id": live_payload.get("cover_media_id", ""),
            "content_media_ids": live_payload.get("content_media_ids", []),
            "authorization_mode": authorization_mode,
            "thumb_result": thumb_result,
            "upload_results": upload_results,
            "draft_response": draft_response,
            "payload": live_payload,
            "normalized_request": wechat_integration.normalize_draft_payload(live_payload),
        }

    def _authorization_mode(self, auth: WeChatAuthorization | None) -> str:
        if not auth:
            return "missing"
        raw_payload = auth.raw_payload or ""
        if "mock-authorize" in raw_payload or auth.authorizer_access_token.startswith("mock-"):
            return "mock"
        return "third_party_platform"

    def _build_publish_payload(self, state: WorkflowState) -> dict:
        editor = state.get("editor", {}).get("result", {})
        formatter = state.get("formatter", {}).get("result", {})
        fact_checker = state.get("fact_checker", {}).get("result", {})
        image_pack = state.get("image_editor", {}).get("result", {}).get("image_asset_pack", {})
        slot_assignments = state.get("image_editor", {}).get("result", {}).get("slot_assignments", [])
        collage = image_pack.get("collage", {}) if isinstance(image_pack, dict) else {}
        images = image_pack.get("images", []) if isinstance(image_pack, dict) else []
        facts_summary = fact_checker.get("facts_summary", {})
        facts_lines = []
        if isinstance(facts_summary, dict):
            for key, value in facts_summary.items():
                facts_lines.append(f"{key}: {value}")
        facts_block = "\n".join(facts_lines)
        body = formatter.get("formatted_body") or state.get("writer", {}).get("result", {}).get("body", "")
        if facts_block:
            body = f"{body}\n\n干货概览\n{facts_block}"
        return {
            "article": {
                "title": editor.get("final_title") or "待发布草稿",
                "author": "林间",
                "summary": editor.get("summary") or "",
                "body": body,
                "content_source_url": "",
                "cover_caption": editor.get("cover_caption") or "",
                "publish_notes": editor.get("publish_notes", []),
            },
            "cover_media_id": "cover_mock",
            "cover_local_path": collage.get("local_path", ""),
            "content_media_ids": [f"content_mock_{idx}" for idx, _ in enumerate(images, start=1)],
            "content_local_paths": [item.get("local_path", "") for item in images if isinstance(item, dict)],
            "image_slots": formatter.get("image_slots", []),
            "slot_assignments": slot_assignments,
            "destination": state.get("destination", ""),
        }

    def _sync_media_assets_after_publish(
        self,
        *,
        session: Session,
        article_job_id: int,
        publish_result: dict,
    ) -> None:
        assets = session.exec(
            select(MediaAsset).where(MediaAsset.article_job_id == article_job_id).order_by(MediaAsset.id.asc())
        ).all()
        cover_media_id = publish_result.get("cover_media_id", "")
        thumb_result = publish_result.get("thumb_result") or {}
        upload_results = publish_result.get("upload_results") or []
        draft_response = publish_result.get("draft_response") or {}

        collage = next((asset for asset in assets if asset.asset_type == "cover_collage"), None)
        if collage:
            collage.wechat_media_id = cover_media_id
            if isinstance(thumb_result, dict):
                collage.wechat_url = str(thumb_result.get("url") or "")
                collage.upload_response_json = json.dumps(thumb_result, ensure_ascii=False)
            session.add(collage)

        image_assets = [asset for asset in assets if asset.asset_type == "image_source"]
        for asset, result in zip(image_assets, upload_results):
            if not isinstance(result, dict):
                continue
            asset.wechat_url = str(result.get("url") or "")
            asset.wechat_media_id = str(result.get("media_id") or "")
            asset.upload_response_json = json.dumps(result, ensure_ascii=False)
            session.add(asset)

        if collage and not collage.upload_response_json and draft_response:
            collage.upload_response_json = json.dumps(draft_response, ensure_ascii=False)
            session.add(collage)

    def _assign_images_to_slots(self, slot_plan: list, images: list) -> list[dict]:
        remaining_images = [item for item in images if isinstance(item, dict)]
        assignments: list[dict] = []
        for item in slot_plan:
            if not isinstance(item, dict):
                continue
            preferred_tag = item.get("preferred_tag", "")
            selected = None
            for candidate in remaining_images:
                metadata = candidate.get("metadata", {})
                if isinstance(metadata, dict) and metadata.get("tag") == preferred_tag:
                    selected = candidate
                    break
            if selected is None and remaining_images:
                selected = remaining_images[0]
            if selected is None:
                continue
            remaining_images = [img for img in remaining_images if img.get("id") != selected.get("id")]
            assignments.append(
                {
                    "slot": item.get("slot", ""),
                    "preferred_tag": preferred_tag,
                    "visual_focus": item.get("visual_focus", ""),
                    "image_id": selected.get("id"),
                    "local_path": selected.get("local_path", ""),
                    "source_url": selected.get("source_url", ""),
                }
            )
        return assignments

    def _execute_agent(self, step_name: str, state: WorkflowState, model_info: dict) -> dict:
        if llm_runtime.can_run(step_name, model_info):
            try:
                output = llm_runtime.invoke_structured(step_name, state, model_info)
                output.setdefault(
                    "decision",
                    f"Use provider {model_info['provider']} and model {model_info['model_name']}",
                )
                output.setdefault("risk_flags", [])
                output.setdefault("retryable", True)
                output["execution_mode"] = "llm"
                return output
            except Exception as exc:
                fallback = self._mock_agent_output(step_name, state, model_info)
                fallback["risk_flags"] = [*fallback.get("risk_flags", []), f"llm_fallback:{exc!s}"]
                fallback["decision"] = (
                    f"Fallback to mock after {model_info['provider']}:{model_info['model_name']} failed"
                )
                fallback["execution_mode"] = "mock_fallback"
                return fallback
        mock = self._mock_agent_output(step_name, state, model_info)
        mock["execution_mode"] = "mock_only"
        return mock

    def _season_theme(self, start_date: str) -> str:
        month = int(start_date.split("-")[1])
        if month in (3, 4, 5):
            return "春日微凉、泥土味、新绿舒展"
        if month in (6, 7, 8):
            return "蝉鸣、晚风、逃离酷暑"
        if month in (9, 10, 11):
            return "桂花香、落叶声、沉静怀旧"
        return "柴火味、热汤雾气、归属感"

    def _mock_agent_output(self, step_name: str, state: WorkflowState, model_info: dict) -> dict:
        prompt = AGENT_PROMPTS[step_name]
        common = {
            "goal": f"Execute {step_name} for article job {state['job_id']}",
            "input_summary": (
                f"Account={state['account_name']}, dates={state['start_date']} to {state['end_date']}"
            ),
            "decision": f"Use provider {model_info['provider']} and model {model_info['model_name']}",
            "risk_flags": [],
            "retryable": True,
        }
        if step_name == "researcher":
            return {
                **common,
                "result": {
                    "destination": "山西晋中左权",
                    "season_theme": state["season_theme"],
                    "facts": {
                        "highway_route": "郑州-焦作-晋城-左权，自驾约3.8小时",
                        "highlights": ["山地村落", "静谧老街", "春季山野新绿"],
                    },
                    "search_preview": state["search_preview"],
                },
            }
        if step_name == "fact_checker":
            return {
                **common,
                "result": {
                    "facts_summary": {
                        "destination": state["destination"],
                        "transport": "推荐自驾，控制在4小时内",
                        "estimated_cost": "900-1300元/家庭",
                        "tips": ["尽量错峰出发", "提前确认民宿接待情况"],
                    },
                    "validation_notes": ["已对目的地与交通信息进行二次核验。"],
                    "rejected_claims": [],
                    "article_alignment": ["写作者初稿中的目的地与交通口径与采集结果一致。"],
                },
            }
        if step_name == "writer":
            return {
                **common,
                "reasoning_check": {
                    "destination": state["destination"],
                    "transport_verified": True,
                    "season_theme": state["season_theme"],
                    "blacklist_checked": True,
                },
                "result": {
                    "title_candidates": [
                        "郑州向西北3.8小时，我在山里找回了一个安静周末",
                        "带娃自驾4小时内，这座省外小城的春风比人群更先抵达",
                        "周末2天2晚，我躲进了一座没有喧闹的山地小城",
                    ],
                    "body": "这是一篇可继续扩写的公众号初稿占位内容，用于串联前后端和工作流。",
                    "closing": "有时候周末真正需要的，不是远行，而是一处能让心慢下来的地方。",
                },
            }
        if step_name == "formatter":
            return {
                **common,
                "result": {
                    "formatted_body": "按公众号段落节奏整理后的正文",
                    "image_slots": ["opening", "day1-food", "day2-street", "closing"],
                },
            }
        if step_name == "editor":
            return {
                **common,
                "result": {
                    "final_title": "郑州向西北3.8小时，我在山里找回了一个安静周末",
                    "summary": "一篇适合周末带娃自驾的省外小众旅行攻略。",
                    "cover_caption": "春风刚刚好，山里正安静。",
                },
            }
        if step_name == "image_editor":
            return {
                **common,
                "result": {
                    "slot_plan": [
                        {
                            "slot": "opening",
                            "preferred_tag": "landmark",
                            "visual_focus": "开篇建立目的地辨识度",
                        },
                        {
                            "slot": "day1-food",
                            "preferred_tag": "food",
                            "visual_focus": "强化地方烟火气和食物记忆点",
                        },
                        {
                            "slot": "day2-street",
                            "preferred_tag": "street_scene",
                            "visual_focus": "补足步行感和街巷松弛感",
                        },
                        {
                            "slot": "closing",
                            "preferred_tag": "nature",
                            "visual_focus": "结尾回到季节气息和呼吸感",
                        },
                    ],
                    "cover_strategy": {
                        "hero_tag": "landmark",
                        "supporting_tags": ["nature", "street_scene", "food"],
                        "layout_note": "杂志风自由拼贴，主视觉突出山景与街巷。",
                    },
                    "required_tags": ["landmark", "nature", "food", "street_scene"],
                    "collage_plan": "杂志风自由拼贴，主视觉突出山景与街巷。",
                    "selection_notes": [
                        "封面优先选地标、山野和街巷混合场景",
                        "正文配图保留美食与街景节奏变化",
                    ],
                },
            }
        return {
            **common,
            "result": {
                "publish_ready": True,
                "missing_assets": [],
                "authorization_mode_hint": "mock",
                "required_actions": [
                    "检查封面素材",
                    "确认正文配图槽位",
                    "整理草稿请求载荷",
                ],
                "dry_run_recommended": True,
            },
        }


workflow_service = WorkflowService()
