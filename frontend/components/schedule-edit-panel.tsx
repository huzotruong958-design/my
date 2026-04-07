"use client";

import { useState, useTransition } from "react";

type ScheduleItem = {
  id: number;
  name: string;
  cron: string;
  timezone: string;
  time_window_start: string;
  time_window_end: string;
  enabled: boolean;
};

export function ScheduleEditPanel({ schedules }: { schedules: ScheduleItem[] }) {
  const [selectedId, setSelectedId] = useState<number>(schedules[0]?.id ?? 0);
  const selected = schedules.find((item) => item.id === selectedId) ?? schedules[0];
  const [form, setForm] = useState({
    name: selected?.name ?? "",
    cron: selected?.cron ?? "",
    timezone: selected?.timezone ?? "Asia/Shanghai",
    time_window_start: selected?.time_window_start ?? "08:00",
    time_window_end: selected?.time_window_end ?? "22:00",
    enabled: selected?.enabled ?? true,
  });
  const [result, setResult] = useState("");
  const [pending, startTransition] = useTransition();

  function syncSelection(nextId: number) {
    const next = schedules.find((item) => item.id === nextId);
    setSelectedId(nextId);
    if (next) {
      setForm({
        name: next.name,
        cron: next.cron,
        timezone: next.timezone,
        time_window_start: next.time_window_start,
        time_window_end: next.time_window_end,
        enabled: next.enabled,
      });
    }
  }

  return (
    <div className="panel stack">
      <div>
        <div className="eyebrow">Edit Schedule</div>
        <h3 style={{ marginBottom: 8 }}>直接调整时间窗和启停</h3>
        <p className="muted">保存后会立即重新注册到服务内调度器。</p>
      </div>
      {schedules.length === 0 ? (
        <div className="muted">当前还没有计划可编辑。</div>
      ) : (
        <>
          <label>
            选择计划
            <select value={selectedId} onChange={(e) => syncSelection(Number(e.target.value))}>
              {schedules.map((schedule) => (
                <option key={schedule.id} value={schedule.id}>
                  {schedule.name}
                </option>
              ))}
            </select>
          </label>
          <div className="grid">
            <label>
              名称
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </label>
            <label>
              Cron
              <input value={form.cron} onChange={(e) => setForm({ ...form, cron: e.target.value })} />
            </label>
            <label>
              开始时间窗
              <input
                value={form.time_window_start}
                onChange={(e) => setForm({ ...form, time_window_start: e.target.value })}
              />
            </label>
            <label>
              结束时间窗
              <input
                value={form.time_window_end}
                onChange={(e) => setForm({ ...form, time_window_end: e.target.value })}
              />
            </label>
          </div>
          <label>
            <span className="muted">启用状态</span>
            <select
              value={String(form.enabled)}
              onChange={(e) => setForm({ ...form, enabled: e.target.value === "true" })}
            >
              <option value="true">启用</option>
              <option value="false">停用</option>
            </select>
          </label>
          <button
            type="button"
            onClick={() =>
              startTransition(async () => {
                const response = await fetch(`http://localhost:8000/api/schedules/${selectedId}`, {
                  method: "PATCH",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify(form),
                });
                const payload = await response.json();
                setResult(JSON.stringify(payload, null, 2));
              })
            }
          >
            {pending ? "保存中..." : "保存修改"}
          </button>
          {result ? <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{result}</pre> : null}
        </>
      )}
    </div>
  );
}

