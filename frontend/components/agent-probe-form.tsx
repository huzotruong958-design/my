"use client";

import { useState, useTransition } from "react";

const defaultState = {
  job_id: 9999,
  tenant_id: 1,
  account_id: 1,
  account_name: "Demo Account",
  start_date: "2026-03-27",
  end_date: "2026-03-29",
  destination: "浙江省丽水市遂昌县",
  season_theme: "春日微凉、泥土味、新绿舒展",
  researcher: {
    result: {
      destination: "浙江省丽水市遂昌县",
      facts: {
        highway_route: "郑州出发自驾路线占位",
        highlights: ["山城", "慢旅行", "春季山野"],
      },
    },
  },
  writer: {
    result: {
      title_candidates: ["郑州出发，周末躲进山里慢两天"],
      body: "我想把这一趟写成一篇有呼吸感的周末旅行稿。",
      closing: "有些地方不是为了打卡，而是为了让人慢下来。",
    },
  },
  fact_checker: {
    result: {
      facts_summary: {
        transport: "建议自驾",
        estimated_cost: "900-1300 元",
      },
    },
  },
  formatter: {
    result: {
      image_slots: ["opening", "day1-food", "day2-street", "closing"],
      formatted_body: "排版后的正文占位",
    },
  },
  editor: {
    result: {
      final_title: "郑州向东南4小时，我在山里找回了周末的呼吸",
      summary: "一篇适合亲子家庭的春日山城周末攻略。",
      cover_caption: "山风正好，街巷安静。",
    },
  },
};

export function AgentProbeForm() {
  const [agentType, setAgentType] = useState("writer");
  const [stateJson, setStateJson] = useState(JSON.stringify(defaultState, null, 2));
  const [result, setResult] = useState("");
  const [pending, startTransition] = useTransition();

  return (
    <div className="panel stack">
      <div>
        <div className="eyebrow">Probe Agent</div>
        <h3 style={{ marginBottom: 8 }}>单独探测真实 Agent 调用</h3>
        <p className="muted">优先用它测试 `writer`，避免每次都跑完整工作流。</p>
      </div>
      <label>
        Agent
        <select value={agentType} onChange={(e) => setAgentType(e.target.value)}>
          <option value="researcher">researcher</option>
          <option value="writer">writer</option>
          <option value="fact_checker">fact_checker</option>
          <option value="formatter">formatter</option>
          <option value="editor">editor</option>
          <option value="image_editor">image_editor</option>
        </select>
      </label>
      <label>
        State JSON
        <textarea rows={18} value={stateJson} onChange={(e) => setStateJson(e.target.value)} />
      </label>
      <button
        type="button"
        onClick={() =>
          startTransition(async () => {
            const response = await fetch("http://localhost:8000/api/debug/probe-agent", {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                tenant_id: 1,
                agent_type: agentType,
                state: JSON.parse(stateJson),
              }),
            });
            const payload = await response.json();
            setResult(JSON.stringify(payload, null, 2));
          })
        }
      >
        {pending ? "探测中..." : "执行单 Agent 探测"}
      </button>
      {result ? <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{result}</pre> : null}
    </div>
  );
}
