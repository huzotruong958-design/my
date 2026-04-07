"use client";

import { useState, useTransition } from "react";

const initialState = {
  tenant_id: 1,
  account_id: 1,
  start_date: "2026-03-27",
  end_date: "2026-03-29",
  audience_profile: "亲子家庭",
  style_preset: "克制、有画面感",
  extra_constraints: "郑州出发，带娃自驾4小时内",
};

export function CreateJobForm() {
  const [form, setForm] = useState(initialState);
  const [result, setResult] = useState<string>("");
  const [pending, startTransition] = useTransition();

  return (
    <div className="panel stack">
      <div>
        <div className="eyebrow">Create Job</div>
        <h3 style={{ marginBottom: 8 }}>立即生成一篇旅行攻略并写入草稿流程</h3>
      </div>
      <div className="grid">
        <label>
          租户 ID
          <input
            value={form.tenant_id}
            onChange={(event) => setForm({ ...form, tenant_id: Number(event.target.value) })}
          />
        </label>
        <label>
          公众号 ID
          <input
            value={form.account_id}
            onChange={(event) => setForm({ ...form, account_id: Number(event.target.value) })}
          />
        </label>
        <label>
          开始日期
          <input
            value={form.start_date}
            onChange={(event) => setForm({ ...form, start_date: event.target.value })}
          />
        </label>
        <label>
          结束日期
          <input
            value={form.end_date}
            onChange={(event) => setForm({ ...form, end_date: event.target.value })}
          />
        </label>
      </div>
      <label>
        受众画像
        <input
          value={form.audience_profile}
          onChange={(event) => setForm({ ...form, audience_profile: event.target.value })}
        />
      </label>
      <label>
        文风预设
        <input
          value={form.style_preset}
          onChange={(event) => setForm({ ...form, style_preset: event.target.value })}
        />
      </label>
      <label>
        额外约束
        <textarea
          rows={3}
          value={form.extra_constraints}
          onChange={(event) => setForm({ ...form, extra_constraints: event.target.value })}
        />
      </label>
      <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <button
          type="button"
          onClick={() =>
            startTransition(async () => {
              const response = await fetch("http://localhost:8000/api/jobs/travel/generate-and-publish", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(form),
              });
              const payload = await response.json();
              setResult(JSON.stringify(payload, null, 2));
            })
          }
        >
          {pending ? "生成中..." : "生成任务"}
        </button>
        <span className="muted">会调用后端 LangGraph 工作流并写入任务记录。</span>
      </div>
      {result ? <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{result}</pre> : null}
    </div>
  );
}

