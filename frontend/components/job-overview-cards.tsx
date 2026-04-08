"use client";

import { JobDetail } from "@/components/job-detail-types";
import { agentLabel, formatDuration } from "@/lib/job-detail";

type JobOverviewCardsProps = {
  detail: JobDetail;
  finalTitle: string;
  summary: string;
};

export function JobOverviewCards({
  detail,
  finalTitle,
  summary,
}: JobOverviewCardsProps) {
  return (
    <div className="grid">
      <div className="panel">
        <div className="eyebrow">Status</div>
        <h3>{detail.job.status}</h3>
        <div className="muted">
          当前步骤：{agentLabel(detail.timing.current_step)} · 已运行 {formatDuration(detail.timing.running_seconds)}
        </div>
        <div className="muted">{detail.job.error_message || "当前没有错误"}</div>
      </div>
      <div className="panel">
        <div className="eyebrow">Draft</div>
        <h3>{detail.publish_record?.draft_id || "尚未写入草稿"}</h3>
        <div className="muted">
          授权模式：
          {detail.publish_record?.authorization_mode || detail.publish_preview?.authorization_mode || "-"} ·
          封面媒体 ID：
          {detail.publish_record?.cover_media_id || "-"}
        </div>
      </div>
      <div className="panel">
        <div className="eyebrow">Final Title</div>
        <h3>{finalTitle || "尚未生成"}</h3>
        <div className="muted">{summary || "暂无摘要"}</div>
      </div>
      <div className="panel">
        <div className="eyebrow">Steps</div>
        <h3>
          {detail.timing.completed_step_count}/{detail.timing.total_step_count}
        </h3>
        <div className="muted">
          下一步：{agentLabel(detail.timing.next_step)} · 总耗时 {formatDuration(detail.timing.completed_seconds)}
        </div>
      </div>
    </div>
  );
}
