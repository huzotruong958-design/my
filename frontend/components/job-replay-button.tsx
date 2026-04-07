"use client";

import { JobActionResult } from "@/components/job-action-result";
import { buildReplayAction } from "@/components/job-action-definitions";
import { useJobAction } from "@/components/use-job-action";

export function JobReplayButton({ jobId }: { jobId: number }) {
  const { pending, result, summary, runJobAction } = useJobAction();

  return (
    <div className="stack">
      <button
        type="button"
        onClick={() => runJobAction(buildReplayAction(jobId))}
      >
        {pending ? "重放中..." : "重放此任务"}
      </button>
      <JobActionResult summary={summary} result={result} />
    </div>
  );
}
