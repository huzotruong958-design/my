"use client";

import { useState, useTransition } from "react";

type ProbeAgentType =
  | "researcher"
  | "writer"
  | "fact_checker"
  | "formatter"
  | "editor"
  | "image_editor"
  | "publisher";

type ProbeConfig = {
  agentType: ProbeAgentType;
  title: string;
  description: string;
  recommendedModel: string;
  recommendedInputs: string[];
  state: Record<string, unknown>;
};

const baseState = {
  job_id: 9999,
  tenant_id: 1,
  account_id: 1,
  account_name: "Demo Account",
  start_date: "2026-04-10",
  end_date: "2026-04-12",
  destination: "待定目的地",
  season_theme: "春日微凉、泥土气、新绿舒展",
  content_strategy_config: {
    departure_city: "郑州",
    transport_mode: "自驾",
    max_transport_hours: 3,
    trip_day_count: 2,
    trip_nights: 1,
    no_repeat_months: 3,
    blacklist: ["西安", "南京"],
    persona_brief: "林间，第一人称旅行作者，中年父亲，强调真实、克制、带娃出游容错率。",
    hard_constraints: "河南省外，小众，避开人潮，自驾 3 小时内优先。",
    seasonal_guidance: "突出春天的光线、气味、微凉体感。",
    title_rules: "标题包含地点或距离、反差、利益点。",
    structure_rules: "开篇、Day1、Day2、返程、实用信息。",
    style_rules: "克制、有画面感、不能研究报告腔。",
    carry_goods_rules: "只推荐便携常温、与当地体验相关的特产。",
  },
  recent_destinations: ["安吉", "榆林"],
  auto_blacklist: ["安吉", "榆林"],
  search_preview: {
    destination: "备选目的地预览占位",
    transport: "郑州出发自驾 3 小时内优先",
  },
};

const probeConfigs: ProbeConfig[] = [
  {
    agentType: "researcher",
    title: "Researcher",
    description: "测试目的地筛选、黑名单约束、小众判断和三个月去重是否生效。",
    recommendedModel: "gemini-3-flash-preview",
    recommendedInputs: [
      "content_strategy_config",
      "recent_destinations",
      "auto_blacklist",
      "start_date / end_date",
      "search_preview",
    ],
    state: baseState,
  },
  {
    agentType: "writer",
    title: "Writer",
    description: "测试文章初稿质量、第一人称叙事和攻略颗粒度。",
    recommendedModel: "gemini-3-pro-preview",
    recommendedInputs: [
      "researcher.result.destination",
      "researcher.result.facts",
      "season_theme",
      "content_strategy_config",
    ],
    state: {
      ...baseState,
      destination: "河北省蔚县",
      researcher: {
        result: {
          destination: "河北省蔚县",
          season_theme: "春风微凉，街巷有烟火气",
          facts: {
            destination_selection: "县城气质明显，游客密度低于周边热门古城。",
            route_plan: "郑州出发，自驾约 2.8 小时，过路费约 120 元。",
            day_1_plan: ["古城街巷", "本地早点", "傍晚城墙边散步"],
            day_2_plan: ["早餐", "周边集市", "午饭后返程"],
            costs: "人均约 700-900 元",
            pitfall_notes: ["周末中午主街停车偏紧张"],
          },
        },
      },
    },
  },
  {
    agentType: "fact_checker",
    title: "Fact Checker",
    description: "测试 writer 初稿与 researcher 底稿的事实冲突裁决。",
    recommendedModel: "gemini-3-flash-preview",
    recommendedInputs: [
      "researcher.result.facts",
      "writer.result.body",
      "writer.result.title_candidates",
      "content_strategy_config",
    ],
    state: {
      ...baseState,
      destination: "河北省蔚县",
      researcher: {
        result: {
          destination: "河北省蔚县",
          facts: {
            route_plan: "郑州出发，自驾约 2.8 小时，过路费约 120 元。",
            costs: "人均约 700-900 元",
          },
        },
      },
      writer: {
        result: {
          title_candidates: ["郑州向北 3 小时，我带孩子去一座安静县城过周末"],
          body: "我从郑州出发，大概 2 个小时就到了，停车不算难。",
          closing: "回城路上，孩子在后排睡着了。",
        },
      },
    },
  },
  {
    agentType: "formatter",
    title: "Formatter",
    description: "测试公众号排版、抽卡信息块和图片插槽节奏。",
    recommendedModel: "gemini-3-flash-preview",
    recommendedInputs: [
      "writer.result.body",
      "fact_checker.result.facts_summary",
      "fact_checker.result.article_alignment",
    ],
    state: {
      ...baseState,
      writer: {
        result: {
          title_candidates: ["郑州出发 3 小时，我在县城过了个不赶路的周末"],
          body: "开篇、Day1、Day2、返程和实用信息都在这里的正文占位。",
          closing: "返程时我带了一袋热饼上车。",
        },
      },
      fact_checker: {
        result: {
          facts_summary: {
            transport: "郑州自驾约 2.8 小时",
            budget: "人均 700-900 元",
          },
          article_alignment: ["保留第一人称", "压缩不确定时长表述"],
        },
      },
    },
  },
  {
    agentType: "editor",
    title: "Editor",
    description: "测试最终标题、摘要、封面文案和发布备注。",
    recommendedModel: "gemini-3-flash-preview",
    recommendedInputs: [
      "formatter.result.formatted_body",
      "writer.result.title_candidates",
      "fact_checker.result.article_alignment",
    ],
    state: {
      ...baseState,
      formatter: {
        result: {
          formatted_body: "排版成稿占位，包含 Day1、Day2、返程、实用信息。",
          image_slots: ["opening", "day1-street", "day1-food", "day2-market", "return"],
          formatting_notes: ["保留慢节奏", "卡片化景点信息"],
        },
      },
      writer: {
        result: {
          title_candidates: [
            "郑州向北不到 3 小时，我在这座安静县城过了个不赶路的周末",
            "带娃从郑州出发 3 小时，我找到一座不拥挤的小城",
          ],
        },
      },
      fact_checker: {
        result: {
          article_alignment: ["距离表述保守", "强调适合亲子家庭"],
        },
      },
    },
  },
  {
    agentType: "image_editor",
    title: "Image Editor",
    description: "测试封面和正文配图规划是否贴合文章叙事。",
    recommendedModel: "gemini-3-flash-preview",
    recommendedInputs: [
      "destination",
      "formatter.result.image_slots",
      "editor.result.final_title",
      "editor.result.summary",
    ],
    state: {
      ...baseState,
      destination: "河北省蔚县",
      formatter: {
        result: {
          image_slots: ["opening", "day1-street", "day1-food", "night", "day2-market", "return"],
        },
      },
      editor: {
        result: {
          final_title: "郑州向北 3 小时，我在这座县城过了个不赶路的周末",
          summary: "适合一家三口的县城周末路线，慢节奏、低拥挤、烟火气足。",
        },
      },
    },
  },
  {
    agentType: "publisher",
    title: "Publisher",
    description: "测试发布前判定、缺失素材检查和 dry run 建议。",
    recommendedModel: "workflow + gemini-3-flash-preview style inputs",
    recommendedInputs: [
      "editor.result",
      "formatter.result",
      "image_editor.result",
      "fact_checker.result",
    ],
    state: {
      ...baseState,
      editor: {
        result: {
          final_title: "郑州向北 3 小时，我在这座县城过了个不赶路的周末",
          summary: "一家三口周末短逃离，重点是慢和稳。",
          cover_caption: "春风正好，街巷安静。",
        },
      },
      formatter: {
        result: {
          formatted_body: "成稿占位",
          image_slots: ["opening", "food", "street", "return"],
        },
      },
      image_editor: {
        result: {
          required_tags: ["street_scene", "food", "landmark"],
          slot_plan: [
            { slot: "opening", preferred_tag: "street_scene", visual_focus: "清晨街巷" },
            { slot: "food", preferred_tag: "food", visual_focus: "热气和手感" },
          ],
        },
      },
    },
  },
];

function ProbeCard({ config }: { config: ProbeConfig }) {
  const [stateJson, setStateJson] = useState(JSON.stringify(config.state, null, 2));
  const [result, setResult] = useState("");
  const [pending, startTransition] = useTransition();

  return (
    <div className="panel stack">
      <div>
        <div className="eyebrow">{config.agentType}</div>
        <h3 style={{ marginBottom: 8 }}>{config.title}</h3>
        <p className="muted">{config.description}</p>
        <p className="muted">推荐模型：{config.recommendedModel}</p>
        <p className="muted">推荐输入：{config.recommendedInputs.join(" · ")}</p>
      </div>
      <label>
        State JSON
        <textarea rows={16} value={stateJson} onChange={(e) => setStateJson(e.target.value)} />
      </label>
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        <button
          type="button"
          onClick={() =>
            startTransition(async () => {
              const response = await fetch("http://localhost:8000/api/debug/probe-agent", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  tenant_id: 1,
                  agent_type: config.agentType,
                  state: JSON.parse(stateJson),
                }),
              });
              const payload = await response.json();
              setResult(JSON.stringify(payload, null, 2));
            })
          }
        >
          {pending ? "探测中..." : `执行 ${config.agentType}`}
        </button>
        <button
          type="button"
          className="secondary"
          onClick={() => {
            setStateJson(JSON.stringify(config.state, null, 2));
            setResult("");
          }}
        >
          恢复预置
        </button>
      </div>
      {result ? <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{result}</pre> : null}
    </div>
  );
}

export function AgentProbeForm() {
  return (
    <div className="stack">
      <div className="panel">
        <div className="eyebrow">Probe Matrix</div>
        <h3 style={{ marginBottom: 8 }}>逐角色单独联调</h3>
        <p className="muted">
          每张卡都是一个独立角色测试入口。你可以直接修改对应 `state JSON`，只重跑当前角色，不影响其他角色。
        </p>
      </div>
      <div className="grid">
        {probeConfigs.map((config) => (
          <ProbeCard key={config.agentType} config={config} />
        ))}
      </div>
    </div>
  );
}
