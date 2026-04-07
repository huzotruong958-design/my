"use client";

import { JobActionResult } from "@/components/job-action-result";
import { buildPublishAction } from "@/components/job-action-definitions";
import { useJobAction } from "@/components/use-job-action";

type PublishExecutePanelProps = {
  jobId: number;
};

export function PublishExecutePanel({ jobId }: PublishExecutePanelProps) {
  const { pending, result, summary, runJobAction } = useJobAction();

  return (
    <div className="panel stack">
      <div>
        <div className="eyebrow">Publish Execute</div>
        <h3 style={{ marginBottom: 8 }}>发布执行入口</h3>
        <p className="muted">默认先做 dry run。只有真实第三方平台授权上下文存在时，实时执行才会真正调用上传和写草稿。</p>
      </div>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <button
          type="button"
          onClick={() => runJobAction(buildPublishAction(jobId, true))}
        >
          {pending ? "执行中..." : "Dry Run 发布"}
        </button>
        <button
          type="button"
          className="secondary"
          onClick={() => runJobAction(buildPublishAction(jobId, false))}
        >
          {pending ? "执行中..." : "实时执行发布"}
        </button>
      </div>
      <JobActionResult summary={summary} result={result} />
    </div>
  );
}
