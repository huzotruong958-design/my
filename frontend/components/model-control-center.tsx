"use client";

import { useMemo, useState, useTransition } from "react";

type Provider = { id: string; label: string };
type Credential = {
  id: number;
  provider: string;
  label: string;
  status: string;
  api_key_masked: string;
  base_url: string;
};
type AgentConfig = {
  id?: number;
  agent_type: string;
  provider: string;
  credential_id?: number | null;
  model_name: string;
  temperature: number;
  max_tokens: number;
  timeout_seconds: number;
  enabled: boolean;
};

type ContentStrategy = {
  config: {
    departure_city: string;
    transport_mode: string;
    max_transport_hours: number;
    trip_day_count: number;
    trip_nights: number;
    no_repeat_months: number;
    persona_brief: string;
    hard_constraints: string;
    blacklist: string[];
    seasonal_guidance: string;
    title_rules: string;
    structure_rules: string;
    style_rules: string;
    carry_goods_rules: string;
  };
  recent_destinations: string[];
  manual_blacklist: string[];
  auto_blacklist: string[];
  destination_history: Array<{
    destination: string;
    selected_at: string;
    job_id?: number;
  }>;
};

const agentLabels: Record<string, string> = {
  researcher: "素材采集者",
  fact_checker: "信息校验者",
  writer: "文章撰写者",
  formatter: "格式校准者",
  editor: "编辑 Agent",
  image_editor: "图片编辑 Agent",
  publisher: "文章发布者",
};

const defaults: Record<string, Omit<AgentConfig, "agent_type">> = {
  researcher: {
    provider: "gemini",
    credential_id: null,
    model_name: "gemini-3-flash-preview",
    temperature: 0.2,
    max_tokens: 3000,
    timeout_seconds: 60,
    enabled: true,
  },
  fact_checker: {
    provider: "gemini",
    credential_id: null,
    model_name: "gemini-3-flash-preview",
    temperature: 0.1,
    max_tokens: 2000,
    timeout_seconds: 60,
    enabled: true,
  },
  writer: {
    provider: "gemini",
    credential_id: null,
    model_name: "gemini-3-pro-preview",
    temperature: 0.7,
    max_tokens: 4500,
    timeout_seconds: 90,
    enabled: true,
  },
  formatter: {
    provider: "gemini",
    credential_id: null,
    model_name: "gemini-3-flash-preview",
    temperature: 0.2,
    max_tokens: 2000,
    timeout_seconds: 60,
    enabled: true,
  },
  editor: {
    provider: "gemini",
    credential_id: null,
    model_name: "gemini-3-flash-preview",
    temperature: 0.2,
    max_tokens: 1500,
    timeout_seconds: 60,
    enabled: true,
  },
  image_editor: {
    provider: "gemini",
    credential_id: null,
    model_name: "gemini-3-flash-preview",
    temperature: 0.3,
    max_tokens: 2000,
    timeout_seconds: 90,
    enabled: true,
  },
  publisher: {
    provider: "openai-compatible",
    credential_id: null,
    model_name: "gpt-4.1-mini",
    temperature: 0.1,
    max_tokens: 1000,
    timeout_seconds: 60,
    enabled: true,
  },
};

export function ModelControlCenter({
  providers,
  credentials,
  configs,
  contentStrategy,
}: {
  providers: Provider[];
  credentials: Credential[];
  configs: AgentConfig[];
  contentStrategy: ContentStrategy;
}) {
  const [credentialForm, setCredentialForm] = useState({
    provider: "gemini",
    label: "Gemini Prod",
    api_key: "",
    base_url: "",
  });
  const [credentialResult, setCredentialResult] = useState("");
  const [configResult, setConfigResult] = useState("");
  const [strategyResult, setStrategyResult] = useState("");
  const [pending, startTransition] = useTransition();
  const [strategyForm, setStrategyForm] = useState({
    ...contentStrategy.config,
    blacklist_text: contentStrategy.config.blacklist.join("\n"),
  });

  const initialRows = useMemo(() => {
    return Object.entries(agentLabels).map(([agentType, label]) => {
      const existing = configs.find((item) => item.agent_type === agentType);
      return {
        agent_type: agentType,
        label,
        ...(existing ?? defaults[agentType]),
      };
    });
  }, [configs]);

  const [rows, setRows] = useState(initialRows);

  const credentialsByProvider = useMemo(() => {
    return credentials.reduce<Record<string, Credential[]>>((acc, item) => {
      acc[item.provider] = acc[item.provider] ?? [];
      acc[item.provider].push(item);
      return acc;
    }, {});
  }, [credentials]);

  function updateRow(agentType: string, key: string, value: string | number | boolean | null) {
    setRows((current) =>
      current.map((row) => (row.agent_type === agentType ? { ...row, [key]: value } : row)),
    );
  }

  return (
    <div className="stack">
      <div className="panel stack">
        <div>
          <div className="eyebrow">Content Strategy</div>
          <h3 style={{ marginBottom: 8 }}>旅行写作策略与目的地去重</h3>
          <p className="muted">这里控制 researcher / writer 等角色共享的出发城市、交通时限、黑名单和目的地冷却周期。</p>
        </div>
        <div className="grid">
          <label>
            出发城市
            <input
              value={strategyForm.departure_city}
              onChange={(e) => setStrategyForm({ ...strategyForm, departure_city: e.target.value })}
            />
          </label>
          <label>
            交通方式
            <input
              value={strategyForm.transport_mode}
              onChange={(e) => setStrategyForm({ ...strategyForm, transport_mode: e.target.value })}
            />
          </label>
          <label>
            最长交通时长
            <input
              value={strategyForm.max_transport_hours}
              onChange={(e) => setStrategyForm({ ...strategyForm, max_transport_hours: Number(e.target.value) })}
            />
          </label>
          <label>
            行程天数
            <input
              value={strategyForm.trip_day_count}
              onChange={(e) => setStrategyForm({ ...strategyForm, trip_day_count: Number(e.target.value) })}
            />
          </label>
          <label>
            住宿夜数
            <input
              value={strategyForm.trip_nights}
              onChange={(e) => setStrategyForm({ ...strategyForm, trip_nights: Number(e.target.value) })}
            />
          </label>
          <label>
            去重周期（月）
            <input
              value={strategyForm.no_repeat_months}
              onChange={(e) => setStrategyForm({ ...strategyForm, no_repeat_months: Number(e.target.value) })}
            />
          </label>
        </div>
        <label>
          人设说明
          <textarea
            rows={4}
            value={strategyForm.persona_brief}
            onChange={(e) => setStrategyForm({ ...strategyForm, persona_brief: e.target.value })}
          />
        </label>
        <label>
          硬性约束
          <textarea
            rows={4}
            value={strategyForm.hard_constraints}
            onChange={(e) => setStrategyForm({ ...strategyForm, hard_constraints: e.target.value })}
          />
        </label>
        <label>
          黑名单
          <textarea
            rows={8}
            value={strategyForm.blacklist_text}
            onChange={(e) => setStrategyForm({ ...strategyForm, blacklist_text: e.target.value })}
            placeholder="每行一个地点"
          />
        </label>
        <label>
          季节引导
          <textarea
            rows={3}
            value={strategyForm.seasonal_guidance}
            onChange={(e) => setStrategyForm({ ...strategyForm, seasonal_guidance: e.target.value })}
          />
        </label>
        <label>
          标题规则
          <textarea
            rows={3}
            value={strategyForm.title_rules}
            onChange={(e) => setStrategyForm({ ...strategyForm, title_rules: e.target.value })}
          />
        </label>
        <label>
          结构规则
          <textarea
            rows={3}
            value={strategyForm.structure_rules}
            onChange={(e) => setStrategyForm({ ...strategyForm, structure_rules: e.target.value })}
          />
        </label>
        <label>
          风格规则
          <textarea
            rows={3}
            value={strategyForm.style_rules}
            onChange={(e) => setStrategyForm({ ...strategyForm, style_rules: e.target.value })}
          />
        </label>
        <label>
          特产/带货规则
          <textarea
            rows={3}
            value={strategyForm.carry_goods_rules}
            onChange={(e) => setStrategyForm({ ...strategyForm, carry_goods_rules: e.target.value })}
          />
        </label>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={() =>
              startTransition(async () => {
                const response = await fetch("http://localhost:8000/api/models/content-strategy", {
                  method: "PUT",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({
                    ...strategyForm,
                    blacklist: strategyForm.blacklist_text
                      .split("\n")
                      .map((item) => item.trim())
                      .filter(Boolean),
                  }),
                });
                const payload = await response.json();
                setStrategyResult(JSON.stringify(payload, null, 2));
              })
            }
          >
            {pending ? "保存中..." : "保存内容策略"}
          </button>
          <span className="muted">researcher 会自动避开最近 {strategyForm.no_repeat_months} 个月已用过的目的地。</span>
        </div>
        {strategyResult ? <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{strategyResult}</pre> : null}
        <div className="panel" style={{ padding: 16 }}>
          <div className="eyebrow">Blacklists</div>
          <p className="muted">
            手工黑名单：{contentStrategy.manual_blacklist.length ? contentStrategy.manual_blacklist.join("、") : "暂无"}
          </p>
          <p className="muted">
            自动黑名单：{contentStrategy.auto_blacklist.length ? contentStrategy.auto_blacklist.join("、") : "暂无"}
          </p>
        </div>
        <div className="panel" style={{ padding: 16 }}>
          <div className="eyebrow">Recent Destinations</div>
          <p className="muted">
            最近冷却中的目的地：{contentStrategy.recent_destinations.length ? contentStrategy.recent_destinations.join("、") : "暂无"}
          </p>
          <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
            {JSON.stringify(contentStrategy.destination_history, null, 2)}
          </pre>
        </div>
      </div>

      <div className="panel stack">
        <div>
          <div className="eyebrow">Credentials</div>
          <h3 style={{ marginBottom: 8 }}>租户级模型凭据</h3>
          <p className="muted">先保存 provider 凭据，再把各个 Agent 绑定到不同模型。</p>
        </div>
        <div className="grid">
          <label>
            Provider
            <select
              value={credentialForm.provider}
              onChange={(e) => setCredentialForm({ ...credentialForm, provider: e.target.value })}
            >
              {providers.map((provider) => (
                <option key={provider.id} value={provider.id}>
                  {provider.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            标签
            <input
              value={credentialForm.label}
              onChange={(e) => setCredentialForm({ ...credentialForm, label: e.target.value })}
            />
          </label>
          <label>
            API Key
            <input
              value={credentialForm.api_key}
              onChange={(e) => setCredentialForm({ ...credentialForm, api_key: e.target.value })}
            />
          </label>
          <label>
            Base URL
            <input
              value={credentialForm.base_url}
              onChange={(e) => setCredentialForm({ ...credentialForm, base_url: e.target.value })}
            />
          </label>
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={() =>
              startTransition(async () => {
                const response = await fetch("http://localhost:8000/api/models/tenants/1/credentials", {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify(credentialForm),
                });
                const payload = await response.json();
                setCredentialResult(JSON.stringify(payload, null, 2));
              })
            }
          >
            {pending ? "保存中..." : "保存凭据"}
          </button>
          <span className="muted">保存后刷新页面即可看到新的可选凭据。</span>
        </div>
        {credentialResult ? <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{credentialResult}</pre> : null}
        <div className="panel" style={{ padding: 16 }}>
          <table>
            <thead>
              <tr>
                <th>Provider</th>
                <th>标签</th>
                <th>Key</th>
                <th>状态</th>
                <th>Base URL</th>
              </tr>
            </thead>
            <tbody>
              {credentials.map((credential) => (
                <tr key={credential.id}>
                  <td>{credential.provider}</td>
                  <td>{credential.label}</td>
                  <td>{credential.api_key_masked || "-"}</td>
                  <td>{credential.status}</td>
                  <td>{credential.base_url || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="panel stack">
        <div>
          <div className="eyebrow">Routing</div>
          <h3 style={{ marginBottom: 8 }}>逐 Agent 模型配置</h3>
          <p className="muted">不同角色可以绑定不同 provider、凭据和模型名，保存后后端会立即按租户生效。</p>
        </div>
        <div style={{ overflowX: "auto" }}>
          <table>
            <thead>
              <tr>
                <th>角色</th>
                <th>Provider</th>
                <th>Credential</th>
                <th>Model</th>
                <th>Temp</th>
                <th>Max Tokens</th>
                <th>Timeout</th>
                <th>启用</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.agent_type}>
                  <td>{row.label}</td>
                  <td>
                    <select
                      value={row.provider}
                      onChange={(e) => {
                        updateRow(row.agent_type, "provider", e.target.value);
                        updateRow(row.agent_type, "credential_id", null);
                      }}
                    >
                      {providers.map((provider) => (
                        <option key={provider.id} value={provider.id}>
                          {provider.label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <select
                      value={row.credential_id ?? ""}
                      onChange={(e) =>
                        updateRow(
                          row.agent_type,
                          "credential_id",
                          e.target.value ? Number(e.target.value) : null,
                        )
                      }
                    >
                      <option value="">未绑定</option>
                      {(credentialsByProvider[row.provider] ?? []).map((credential) => (
                        <option key={credential.id} value={credential.id}>
                          {credential.label}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td>
                    <input
                      value={row.model_name}
                      onChange={(e) => updateRow(row.agent_type, "model_name", e.target.value)}
                    />
                  </td>
                  <td>
                    <input
                      value={row.temperature}
                      onChange={(e) => updateRow(row.agent_type, "temperature", Number(e.target.value))}
                    />
                  </td>
                  <td>
                    <input
                      value={row.max_tokens}
                      onChange={(e) => updateRow(row.agent_type, "max_tokens", Number(e.target.value))}
                    />
                  </td>
                  <td>
                    <input
                      value={row.timeout_seconds}
                      onChange={(e) =>
                        updateRow(row.agent_type, "timeout_seconds", Number(e.target.value))
                      }
                    />
                  </td>
                  <td>
                    <input
                      type="checkbox"
                      checked={row.enabled}
                      onChange={(e) => updateRow(row.agent_type, "enabled", e.target.checked)}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={() =>
              startTransition(async () => {
                const agents = Object.fromEntries(
                  rows.map((row) => [
                    row.agent_type,
                    {
                      provider: row.provider,
                      credential_id: row.credential_id || null,
                      model_name: row.model_name,
                      temperature: row.temperature,
                      max_tokens: row.max_tokens,
                      timeout_seconds: row.timeout_seconds,
                      enabled: row.enabled,
                      extra_params: {},
                    },
                  ]),
                );
                const response = await fetch("http://localhost:8000/api/models/tenants/1/agent-configs", {
                  method: "PUT",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ agents }),
                });
                const payload = await response.json();
                setConfigResult(JSON.stringify(payload, null, 2));
              })
            }
          >
            {pending ? "保存中..." : "保存全部 Agent 配置"}
          </button>
          <span className="muted">真实 LLM 调用会优先使用这里保存的 provider、model 和 credential。</span>
        </div>
        {configResult ? <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{configResult}</pre> : null}
      </div>
    </div>
  );
}
