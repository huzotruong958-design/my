"use client";

import { prettyJson } from "@/lib/job-detail";

type JobMergedStateSectionProps = {
  parsedOutput: Record<string, unknown>;
};

export function JobMergedStateSection({
  parsedOutput,
}: JobMergedStateSectionProps) {
  return (
    <div className="panel stack">
      <div className="eyebrow">Merged State</div>
      <h3 style={{ marginTop: 0 }}>最终工作流状态</h3>
      <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{prettyJson(parsedOutput)}</pre>
    </div>
  );
}
