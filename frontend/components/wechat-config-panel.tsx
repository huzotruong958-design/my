"use client";

import { useState, useTransition } from "react";

type ConfigStatus = {
  component_app_id_configured: boolean;
  component_app_secret_configured: boolean;
  component_token_configured: boolean;
  component_aes_key_configured: boolean;
  callback_base_url: string;
  ready_for_real_auth: boolean;
  has_component_verify_ticket?: boolean;
  has_component_access_token?: boolean;
  component_access_token_expires_at?: string;
  component_access_token_valid?: boolean;
  has_pre_auth_code?: boolean;
  pre_auth_code_expires_at?: string;
  pre_auth_code_valid?: boolean;
  last_callback_info_type?: string;
  last_callback_at?: string;
  last_callback_raw_xml?: string;
};

type BindingGuide = {
  tenant_id: number;
  mode: string;
  ready_for_real_auth: boolean;
  callback_url: string;
  notes: string[];
  endpoints: Record<string, unknown>;
};

export function WeChatConfigPanel({
  config,
  guide,
}: {
  config: ConfigStatus;
  guide: BindingGuide;
}) {
  const [ticket, setTicket] = useState("");
  const [result, setResult] = useState("");
  const [pending, startTransition] = useTransition();

  async function postAction(path: string, body?: unknown) {
    const response = await fetch(`http://localhost:8000/api${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: body ? JSON.stringify(body) : undefined,
    });
    const payload = await response.json();
    setResult(JSON.stringify(payload, null, 2));
  }

  return (
    <div className="panel stack">
      <div>
        <div className="eyebrow">WeChat Config</div>
        <h3 style={{ marginBottom: 8 }}>第三方平台接入状态</h3>
        <p className="muted">这部分用于判断当前环境是否已经具备真实微信公众号授权的配置条件，并管理 component ticket/token/pre-auth-code。</p>
      </div>
      <div className="grid">
        <div className="panel" style={{ padding: 16 }}>
          <div className="eyebrow">Component App ID</div>
          <strong>{String(config.component_app_id_configured)}</strong>
        </div>
        <div className="panel" style={{ padding: 16 }}>
          <div className="eyebrow">Component Secret</div>
          <strong>{String(config.component_app_secret_configured)}</strong>
        </div>
        <div className="panel" style={{ padding: 16 }}>
          <div className="eyebrow">Component Token</div>
          <strong>{String(config.component_token_configured)}</strong>
        </div>
        <div className="panel" style={{ padding: 16 }}>
          <div className="eyebrow">AES Key</div>
          <strong>{String(config.component_aes_key_configured)}</strong>
        </div>
      </div>
      <div className="grid">
        <div className="panel" style={{ padding: 16 }}>
          <div className="eyebrow">Real Auth Ready</div>
          <h3 style={{ marginTop: 8 }}>{String(config.ready_for_real_auth)}</h3>
          <div className="muted">Callback Base URL: {config.callback_base_url}</div>
        </div>
        <div className="panel" style={{ padding: 16 }}>
          <div className="eyebrow">Component Ticket</div>
          <strong>{String(config.has_component_verify_ticket ?? false)}</strong>
        </div>
        <div className="panel" style={{ padding: 16 }}>
          <div className="eyebrow">Component Token Cache</div>
          <strong>{String(config.component_access_token_valid ?? false)}</strong>
          <div className="muted">{config.component_access_token_expires_at || "未缓存"}</div>
        </div>
        <div className="panel" style={{ padding: 16 }}>
          <div className="eyebrow">Pre Auth Code Cache</div>
          <strong>{String(config.pre_auth_code_valid ?? false)}</strong>
          <div className="muted">{config.pre_auth_code_expires_at || "未缓存"}</div>
        </div>
        <div className="panel" style={{ padding: 16 }}>
          <div className="eyebrow">Last Callback</div>
          <strong>{config.last_callback_info_type || "暂无"}</strong>
          <div className="muted">{config.last_callback_at || "暂无回调记录"}</div>
        </div>
      </div>
      <div className="panel stack" style={{ padding: 16 }}>
        <div className="eyebrow">Component Runtime</div>
        <label>
          手动保存 Component Verify Ticket
          <input value={ticket} onChange={(event) => setTicket(event.target.value)} placeholder="ticket_xxx" />
        </label>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <button
            type="button"
            onClick={() =>
              startTransition(async () => {
                await postAction("/accounts/wechat/component-ticket", {
                  component_verify_ticket: ticket,
                });
              })
            }
          >
            {pending ? "处理中..." : "保存 Ticket"}
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() =>
              startTransition(async () => {
                await postAction("/accounts/wechat/component/callback/mock", {
                  info_type: "component_verify_ticket",
                  component_verify_ticket: ticket || "mock-component-ticket",
                });
              })
            }
          >
            {pending ? "处理中..." : "模拟 Callback"}
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() =>
              startTransition(async () => {
                await postAction("/accounts/wechat/component-access-token/refresh");
              })
            }
          >
            {pending ? "处理中..." : "刷新 Component Token"}
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() =>
              startTransition(async () => {
                await postAction("/accounts/wechat/pre-auth-code/refresh");
              })
            }
          >
            {pending ? "处理中..." : "刷新 Pre Auth Code"}
          </button>
        </div>
        {result ? <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{result}</pre> : null}
      </div>
      <div className="panel" style={{ padding: 16 }}>
        <div className="eyebrow">Last Callback XML</div>
        <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
          {config.last_callback_raw_xml || "暂无原始回调 XML"}
        </pre>
      </div>
      <div className="panel" style={{ padding: 16 }}>
        <div className="eyebrow">Binding Guide</div>
        <div className="muted">模式：{guide.mode}</div>
        <div className="muted">回调地址：{guide.callback_url}</div>
        <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{JSON.stringify(guide.notes, null, 2)}</pre>
      </div>
      <div className="panel" style={{ padding: 16 }}>
        <div className="eyebrow">Endpoint Blueprint</div>
        <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{JSON.stringify(guide.endpoints, null, 2)}</pre>
      </div>
    </div>
  );
}
