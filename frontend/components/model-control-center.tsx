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
    model_name: "gemini-2.5-pro",
    temperature: 0.2,
    max_tokens: 3000,
    timeout_seconds: 60,
    enabled: true,
  },
  fact_checker: {
    provider: "openai-compatible",
    credential_id: null,
    model_name: "gpt-4.1-mini",
    temperature: 0.1,
    max_tokens: 2000,
    timeout_seconds: 60,
    enabled: true,
  },
  writer: {
    provider: "gemini",
    credential_id: null,
    model_name: "gemini-2.5-pro",
    temperature: 0.7,
    max_tokens: 4500,
    timeout_seconds: 90,
    enabled: true,
  },
  formatter: {
    provider: "anthropic",
    credential_id: null,
    model_name: "claude-3-7-sonnet",
    temperature: 0.2,
    max_tokens: 2000,
    timeout_seconds: 60,
    enabled: true,
  },
  editor: {
    provider: "openai-compatible",
    credential_id: null,
    model_name: "gpt-4.1-mini",
    temperature: 0.2,
    max_tokens: 1500,
    timeout_seconds: 60,
    enabled: true,
  },
  image_editor: {
    provider: "gemini",
    credential_id: null,
    model_name: "gemini-2.5-pro",
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
}: {
  providers: Provider[];
  credentials: Credential[];
  configs: AgentConfig[];
}) {
  const [credentialForm, setCredentialForm] = useState({
    provider: "gemini",
    label: "Gemini Prod",
    api_key: "",
    base_url: "",
  });
  const [credentialResult, setCredentialResult] = useState("");
  const [configResult, setConfigResult] = useState("");
  const [pending, startTransition] = useTransition();

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

