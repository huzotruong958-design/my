"use client";

import { PublishPreviewDetail, PublishRecordDetail } from "@/components/job-detail-types";
import { prettyJson } from "@/lib/job-detail";

type JobPublishSectionProps = {
  publishPreview: PublishPreviewDetail;
  publishResult: Record<string, unknown>;
  publishRecord: PublishRecordDetail | null;
};

export function JobPublishSection({
  publishPreview,
  publishResult,
  publishRecord,
}: JobPublishSectionProps) {
  const publishReadiness = publishPreview?.publish_readiness ?? {};
  const publishPayload = publishPreview?.publish_payload ?? {};
  const publishBundle = publishPreview?.publish_bundle ?? {};
  const authorizationContext = publishPreview?.authorization_context ?? {};

  return (
    <>
      <div className="grid">
        <div className="panel stack">
          <div className="eyebrow">Publish Readiness</div>
          <h3 style={{ marginTop: 0 }}>发布判定</h3>
          <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
            {prettyJson({
              publish_ready: publishReadiness.publish_ready,
              missing_assets: publishReadiness.missing_assets,
              authorization_mode: publishPreview?.authorization_mode,
              authorization_mode_hint: publishReadiness.authorization_mode_hint,
              required_actions: publishReadiness.required_actions,
              dry_run_recommended: publishReadiness.dry_run_recommended,
            })}
          </pre>
        </div>
        <div className="panel stack">
          <div className="eyebrow">Draft Payload</div>
          <h3 style={{ marginTop: 0 }}>发布前组装结果</h3>
          <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{prettyJson(publishPayload)}</pre>
        </div>
        <div className="panel stack">
          <div className="eyebrow">Draft Request</div>
          <h3 style={{ marginTop: 0 }}>标准化草稿请求</h3>
          <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
            {prettyJson(publishBundle.draft_request || {})}
          </pre>
        </div>
        <div className="panel stack">
          <div className="eyebrow">Publish Response</div>
          <h3 style={{ marginTop: 0 }}>发布响应</h3>
          <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{prettyJson(publishResult || {})}</pre>
        </div>
      </div>

      <div className="grid">
        <div className="panel stack">
          <div className="eyebrow">Authorization Context</div>
          <h3 style={{ marginTop: 0 }}>公众号授权上下文</h3>
          <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
            {prettyJson(authorizationContext)}
          </pre>
        </div>
        <div className="panel stack">
          <div className="eyebrow">Thumb Request</div>
          <h3 style={{ marginTop: 0 }}>封面上传请求预览</h3>
          <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
            {prettyJson(publishBundle.thumb_request || {})}
          </pre>
        </div>
        <div className="panel stack">
          <div className="eyebrow">Upload Requests</div>
          <h3 style={{ marginTop: 0 }}>图片上传请求预览</h3>
          <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
            {prettyJson(publishBundle.upload_requests || [])}
          </pre>
        </div>
      </div>

      <div className="grid">
        <div className="panel stack">
          <div className="eyebrow">Thumb Result</div>
          <h3 style={{ marginTop: 0 }}>封面上传结果</h3>
          <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
            {prettyJson(publishRecord?.thumb_result || {})}
          </pre>
        </div>
        <div className="panel stack">
          <div className="eyebrow">Upload Results</div>
          <h3 style={{ marginTop: 0 }}>正文图片上传结果</h3>
          <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
            {prettyJson(publishRecord?.upload_results || [])}
          </pre>
        </div>
        <div className="panel stack">
          <div className="eyebrow">Draft Response</div>
          <h3 style={{ marginTop: 0 }}>草稿提交结果</h3>
          <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
            {prettyJson(publishRecord?.draft_response || {})}
          </pre>
        </div>
      </div>
    </>
  );
}
