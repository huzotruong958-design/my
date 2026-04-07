"use client";

import { useState, useTransition } from "react";

export function CreateScheduleForm() {
  const [form, setForm] = useState({
    tenant_id: 1,
    official_account_id: 1,
    name: "周五晚自动生成",
    cron: "0 18 * * 5",
    timezone: "Asia/Shanghai",
    time_window_start: "18:00",
    time_window_end: "21:00",
    enabled: true,
  });
  const [result, setResult] = useState("");
  const [pending, startTransition] = useTransition();

  return (
    <div className="panel stack">
      <div>
        <div className="eyebrow">Schedule</div>
        <h3 style={{ marginBottom: 8 }}>为公众号新增定时计划</h3>
      </div>
      <div className="grid">
        <label>
          租户 ID
          <input value={form.tenant_id} onChange={(e) => setForm({ ...form, tenant_id: Number(e.target.value) })} />
        </label>
        <label>
          公众号 ID
          <input
            value={form.official_account_id}
            onChange={(e) => setForm({ ...form, official_account_id: Number(e.target.value) })}
          />
        </label>
        <label>
          计划名称
          <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </label>
        <label>
          Cron
          <input value={form.cron} onChange={(e) => setForm({ ...form, cron: e.target.value })} />
        </label>
      </div>
      <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <button
          type="button"
          onClick={() =>
            startTransition(async () => {
              const response = await fetch("http://localhost:8000/api/schedules", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(form),
              });
              const payload = await response.json();
              setResult(JSON.stringify(payload, null, 2));
            })
          }
        >
          {pending ? "保存中..." : "保存计划"}
        </button>
      </div>
      {result ? <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{result}</pre> : null}
    </div>
  );
}

