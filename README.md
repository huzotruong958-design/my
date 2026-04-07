# WeChat Travel Agents

Full-stack starter for a multi-agent WeChat article pipeline:

- FastAPI backend for orchestration, scheduling, model routing, and WeChat auth binding
- Next.js admin UI for accounts, tasks, schedules, and model configuration
- LangChain/LangGraph-oriented agent definitions with structured prompts

## Quick start

### Backend

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Notes

- Repository Python is pinned to `3.14.3` via `.python-version`.
- The backend defaults to SQLite for local development and can be switched to PostgreSQL with `DATABASE_URL`.
- WeChat third-party-platform auth now includes component ticket/token/pre-auth-code cache, callback receiver shape, and publish dry-run/live execution entry points.
- Image assets are now generated through a pluggable provider layer. Local default is `mock-xiaohongshu`, and `demo-remote-photo` can download sample photos into `backend/media/`.

## Local integration flow

1. Start the backend and frontend.
2. Open the dashboard and check `Readiness`.
3. In `模型配置`, add at least one validated provider credential if you want real LLM calls.
4. In `公众号账号`, either:
   - use real third-party-platform auth after filling WeChat component env vars, or
   - use `本地 Mock 授权` for local testing.
5. In `定时计划`, create or edit a schedule and widen the time window for local smoke tests.
6. Use `立即执行` to test scheduler-triggered generation.
7. Use `任务与产物` to inspect each Agent step, model route, execution mode, and final draft payload.
8. Open a job detail page to preview generated media assets directly from `/media/...`.
9. In `公众号账号`, you can now:
   - save a `component_verify_ticket`
   - simulate a component callback locally
   - refresh `component_access_token`
   - refresh `pre_auth_code`
10. In a job detail page, use `Dry Run 发布` before trying `实时执行发布`.

## WeChat callback endpoints

- `GET /api/accounts/wechat/component/callback`
  - echo verification entry
- `POST /api/accounts/wechat/component/callback`
  - receives third-party platform callback XML and stores:
    - `InfoType`
    - `ComponentVerifyTicket`
    - raw XML
- `POST /api/accounts/wechat/component/callback/mock`
  - local mock callback helper for component ticket flow

## Publish flow

- `GET /api/jobs/{job_id}/publish-preview`
  - rebuilds the current publish bundle from job output and account auth state
  - response shape is aligned to include:
    - `mode=preview`
    - `publish_preview`
    - `publish_result`
    - `publish_record`
- `GET /api/jobs/{job_id}`
  - now also includes `publish_preview`, so task detail pages can read a unified:
    - `authorization_mode`
    - `authorization_context`
    - `publish_payload`
    - `publish_bundle`
    - `publish_readiness`
  - also includes `publish_result`
    - prefer this over reading nested `publisher.result.publish_response`
- `POST /api/jobs/{job_id}/publish-execute`
  - `dry_run=true`: preview only
  - `dry_run=false`: if account auth mode is `third_party_platform`, executes:
    1. thumb upload
    2. article image uploads
    3. draft submit
  - both dry-run and live execution now return `publish_preview`
  - response shape is aligned to include:
    - `mode`
    - `publish_preview`
    - `publish_result`
    - `publish_record`

## Job image refresh

- `POST /api/jobs/{job_id}/refresh-images`
  - rebuilds the current job media pack using the active image provider
  - refreshes:
    - `image_asset_pack`
    - `slot_assignments`
    - `provider_context`
    - `publish_preview` derived from the latest media files
  - response shape now also includes:
    - `mode=refresh_images`
    - `publish_result`
    - `publish_record`
  - useful after:
    - switching image provider mode
    - editing the external image manifest

## External image manifest

- `GET /api/search/external-image-manifest`
  - reads the current persisted image URL manifest
- `PUT /api/search/external-image-manifest`
  - writes the manifest used by `external-url-ingest`
- `GET /api/search/image-providers`
  - also returns:
    - `manifest_count`
    - `manifest_preview`

Each manifest item can include:

```json
{
  "url": "https://example.com/demo.jpg",
  "tag": "nature",
  "title": "River walk",
  "source_page": "https://example.com/article"
}
```

## Image provider modes

- `mock-xiaohongshu`
  - generates local SVG image assets and collage files
- `demo-remote-photo`
  - downloads remote demo photos for local media testing
- `external-url-ingest`
  - downloads images from a saved URL manifest
  - each item can carry `tag`, `title`, and `source_page`
  - useful for plugging in future Xiaohongshu or custom crawler output without changing the publish pipeline
- `xiaohongshu-mcp`
  - preferred production mode for Xiaohongshu ingestion
  - calls an external Xiaohongshu MCP service for keyword search and note-detail extraction
  - first login persistence is handled by the MCP service itself
  - this project stores MCP endpoint, optional token, timeout, and last probe result
- `xiaohongshu-note-scrape`
  - fetches public Xiaohongshu note pages from a saved seed-url list
  - extracts note title/description/image URLs from public HTML/meta payloads
  - downloads extracted images into the same media pipeline used by publishing
  - if no seed URLs are saved, it can auto-discover public note URLs from destination/title/summary context via search-engine queries

## Xiaohongshu seed routes

- `GET /api/search/xiaohongshu-seed-urls`
  - returns the saved Xiaohongshu note seed URLs
- `PUT /api/search/xiaohongshu-seed-urls`
  - saves the Xiaohongshu note seed URLs
- `POST /api/search/xiaohongshu-preview`
  - fetches the current seed URLs and previews extracted note/image payloads
  - if `urls` is empty, it can auto-discover note URLs from:
    - `destination`
    - `title`
    - `summary`
- `GET /api/search/xiaohongshu-mcp-config`
  - reads the persisted MCP endpoint / timeout / probe status
- `PUT /api/search/xiaohongshu-mcp-config`
  - saves MCP endpoint / bearer token / timeout / enabled flag
- `POST /api/search/xiaohongshu-mcp-probe`
  - initializes the MCP connection
  - lists available tools
  - probes login-status capability when the MCP server exposes it

## Current execution modes

- `llm`: real model call succeeded
- `mock_fallback`: real call was attempted but failed, so the workflow fell back to mock output
- `mock_only`: no real credential/config was available, so mock output was used directly

## Task detail observability

Each job detail page now exposes:

- per-Agent `provider / model / execution_mode`
- `image_source_summary` for the actual media source mix
- `provider_context` for the image pipeline used by that run
- stored media records with local preview URLs and WeChat upload results
- unified publish preview and live publish results
- publish readiness fields:
  - `publish_ready`
  - `missing_assets`
  - `dry_run_recommended`
  - `authorization_mode_hint`
  - `required_actions`
- unified action-result cards for:
  - replay
  - refresh images
  - publish execute
- shared client-side job action helper is used by those controls to keep:
  - request behavior
  - summary generation
  - page refresh flow
  consistent
- action summaries are also centralized, so replay / refresh / publish use the same summary formatting layer
- job action request definitions are centralized too, so those controls share:
  - path construction
  - request method/body
  - action-specific summary mapping
- shared frontend response types are used for those actions, reducing ad-hoc `any` parsing in UI controls
- job detail page types are also extracted, keeping the page focused on rendering instead of inline type blocks
- parsed-output helper types for writer / editor / formatter / fact checker / image editor are also centralized
- job detail rendering helpers such as JSON pretty-printing and execution-mode labels are extracted into shared utils
- static job-detail label maps such as Agent display names are extracted as shared constants too
- publish-preview derived values used by the job detail page are normalized through a shared helper
- parsed workflow outputs used by the job detail page are also resolved through a shared helper
- large job-detail display regions such as image/media panels and publish panels are split into dedicated components
- top-level job overview cards and article preview/facts panels are also split into dedicated components
- timeline rendering and merged workflow-state rendering are also split into dedicated components
- inline table renderers on the accounts and schedules pages are extracted into dedicated table components
- account and schedule row shapes are centralized as shared admin-page types
- shared page-level section components now cover common admin UI blocks such as page heroes, auth launch panels, and provider grids

## Replay job

- `POST /api/jobs/{job_id}/replay`
  - creates a new job from the original payload and reruns the workflow
  - response shape now includes:
    - `mode=replay`
    - `job`
    - `publish_result`
    - `publish_record`
