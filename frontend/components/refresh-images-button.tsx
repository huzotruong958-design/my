"use client";

import { JobActionResult } from "@/components/job-action-result";
import { buildRefreshImagesAction } from "@/components/job-action-definitions";
import { useJobAction } from "@/components/use-job-action";

export function RefreshImagesButton({ jobId }: { jobId: number }) {
  const { pending, result, summary, runJobAction } = useJobAction();

  return (
    <div className="stack">
      <button
        type="button"
        className="secondary"
        onClick={() => runJobAction(buildRefreshImagesAction(jobId))}
      >
        {pending ? "重建中..." : "重建图片资产"}
      </button>
      <JobActionResult summary={summary} result={result} />
    </div>
  );
}
