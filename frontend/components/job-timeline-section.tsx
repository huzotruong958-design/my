"use client";

import Link from "next/link";

import { JobStepDetail } from "@/components/job-detail-types";
import { JobReplayButton } from "@/components/job-replay-button";
import { RefreshImagesButton } from "@/components/refresh-images-button";
import { agentLabels, executionModeLabel, prettyJson } from "@/lib/job-detail";

type JobTimelineSectionProps = {
  jobId: number;
  steps: JobStepDetail[];
};

export function JobTimelineSection({
  jobId,
  steps,
}: JobTimelineSectionProps) {
  return (
    <div className="panel stack">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <div className="eyebrow">Timeline</div>
          <h3 style={{ marginBottom: 8 }}>逐 Agent 运行详情</h3>
        </div>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <JobReplayButton jobId={jobId} />
          <RefreshImagesButton jobId={jobId} />
          <Link className="button secondary" href="/jobs">
            返回任务列表
          </Link>
        </div>
      </div>
      {steps.map((step) => (
        <div key={step.id} className="panel stack" style={{ padding: 16 }}>
          <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
            <div>
              <div className="eyebrow">{step.agent_name}</div>
              <h4 style={{ marginTop: 6, marginBottom: 6 }}>
                {agentLabels[step.agent_name] ?? step.agent_name}
              </h4>
            </div>
            <div className="muted">
              {step.model_provider} / {step.model_name}
            </div>
          </div>
          <div className="muted">执行状态：{step.status}</div>
          <div className="muted">
            执行模式：
            {executionModeLabel(
              (() => {
                try {
                  const parsed = JSON.parse(step.output_json);
                  return parsed.execution_mode as string | undefined;
                } catch {
                  return undefined;
                }
              })(),
            )}
          </div>
          <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{prettyJson(step.output_json)}</pre>
        </div>
      ))}
    </div>
  );
}
