"use client";

import { ImageEditorOutput, ImageSourceSummary, MediaAssetDetail } from "@/components/job-detail-types";
import { prettyJson } from "@/lib/job-detail";

type JobImageSectionProps = {
  imageEditor?: ImageEditorOutput;
  imageSourceSummary: ImageSourceSummary;
  mediaAssets: MediaAssetDetail[];
};

export function JobImageSection({
  imageEditor,
  imageSourceSummary,
  mediaAssets,
}: JobImageSectionProps) {
  return (
    <div className="grid">
      <div className="panel stack">
        <div className="eyebrow">Image Pack</div>
        <h3 style={{ marginTop: 0 }}>图片资产与拼图产物</h3>
        <div className="muted">{imageEditor?.result?.collage_plan || "暂无拼图方案"}</div>
        <div className="eyebrow">Provider Context</div>
        <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
          {prettyJson(imageEditor?.result?.provider_context || {})}
        </pre>
        <div className="eyebrow">Image Source Summary</div>
        <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
          {prettyJson(imageSourceSummary || {})}
        </pre>
        <div className="eyebrow">Cover Strategy</div>
        <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
          {prettyJson(imageEditor?.result?.cover_strategy || {})}
        </pre>
        <div className="eyebrow">Required Tags</div>
        <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
          {prettyJson(imageEditor?.result?.required_tags || [])}
        </pre>
        <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
          {prettyJson(imageEditor?.result?.selection_notes || [])}
        </pre>
        <div className="eyebrow">Slot Assignments</div>
        <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
          {prettyJson(imageEditor?.result?.slot_assignments || [])}
        </pre>
        <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
          {prettyJson(imageEditor?.result?.image_asset_pack || {})}
        </pre>
      </div>

      <div className="panel stack">
        <div className="eyebrow">Stored Media</div>
        <h3 style={{ marginTop: 0 }}>已落库素材</h3>
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: 16,
          }}
        >
          {mediaAssets.map((asset) => (
            <div
              key={asset.id}
              className="panel stack"
              style={{ padding: 12, background: "rgba(255,255,255,0.7)" }}
            >
              {asset.media_url ? (
                <a href={asset.media_url} target="_blank" rel="noreferrer">
                  <img
                    src={asset.media_url}
                    alt={`${asset.asset_type}-${asset.id}`}
                    style={{
                      width: "100%",
                      aspectRatio: "4 / 3",
                      objectFit: "cover",
                      borderRadius: 12,
                      border: "1px solid rgba(0,0,0,0.08)",
                      background: "#f3f0ea",
                    }}
                  />
                </a>
              ) : null}
              <div className="eyebrow">{asset.asset_type}</div>
              <strong>#{asset.id}</strong>
              <div className="muted">上传角色：{asset.upload_role || "-"}</div>
              <div className="muted" style={{ wordBreak: "break-all" }}>
                {asset.local_path}
              </div>
              <div className="muted" style={{ wordBreak: "break-all" }}>
                微信 media_id：{asset.wechat_media_id || "-"}
              </div>
              <div className="muted" style={{ wordBreak: "break-all" }}>
                微信 url：{asset.wechat_url || "-"}
              </div>
              {asset.source_url ? (
                <a
                  className="muted"
                  href={asset.source_url}
                  target="_blank"
                  rel="noreferrer"
                  style={{ wordBreak: "break-all" }}
                >
                  来源链接
                </a>
              ) : null}
              <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
                {prettyJson(asset.metadata || {})}
              </pre>
              <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
                {prettyJson(asset.upload_response || {})}
              </pre>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
