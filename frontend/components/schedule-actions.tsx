"use client";

import { useState, useTransition } from "react";

type ScheduleItem = {
  id: number;
  name: string;
  enabled: boolean;
  next_run_time?: string | null;
  last_run?: {
    status: string;
    message: string;
    attempt: number;
    created_at: string;
    article_job_id?: number | null;
    trigger_type: string;
  } | null;
};

export function ScheduleActions({ schedules }: { schedules: ScheduleItem[] }) {
  const [result, setResult] = useState("");
  const [pending, startTransition] = useTransition();

  return (
    <div className="panel stack">
      <div>
        <div className="eyebrow">Run Now</div>
        <h3 style={{ marginBottom: 8 }}>手动触发计划</h3>
        <p className="muted">用于验证时间窗、授权状态、自动重试和任务生成链路。</p>
      </div>
      <div className="stack">
        {schedules.map((schedule) => (
          <div
            key={schedule.id}
            className="panel"
            style={{ padding: 16, display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}
          >
            <div>
              <div className="eyebrow">{schedule.next_run_time || "暂无下次执行时间"}</div>
              <strong>{schedule.name}</strong>
              <div className="muted">
                最近执行：{schedule.last_run?.status || "暂无"} · {schedule.last_run?.message || "暂无执行记录"}
              </div>
            </div>
            <button
              type="button"
              disabled={!schedule.enabled}
              onClick={() =>
                startTransition(async () => {
                  const response = await fetch(`http://localhost:8000/api/schedules/${schedule.id}/run-now`, {
                    method: "POST",
                  });
                  const payload = await response.json();
                  setResult(JSON.stringify(payload, null, 2));
                })
              }
            >
              {pending ? "触发中..." : "立即执行"}
            </button>
          </div>
        ))}
      </div>
      {result ? <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{result}</pre> : null}
    </div>
  );
}
