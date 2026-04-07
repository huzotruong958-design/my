"use client";

import { useState, useTransition } from "react";

type Account = {
  id: number;
  display_name: string;
  wechat_app_id: string;
  status: string;
};

export function AccountTestActions({ accounts }: { accounts: Account[] }) {
  const [result, setResult] = useState("");
  const [pending, startTransition] = useTransition();

  return (
    <div className="panel stack">
      <div>
        <div className="eyebrow">Local Test</div>
        <h3 style={{ marginBottom: 8 }}>本地 Mock 授权</h3>
        <p className="muted">没有真实微信凭据时，用这个入口把公众号账号切到 `publishable`，便于测试定时任务和草稿链路。</p>
      </div>
      <div className="stack">
        {accounts.map((account) => (
          <div
            key={account.id}
            className="panel"
            style={{ padding: 16, display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}
          >
            <div>
              <div className="eyebrow">{account.wechat_app_id}</div>
              <strong>{account.display_name}</strong>
              <div className="muted">当前状态：{account.status}</div>
            </div>
            <button
              type="button"
              onClick={() =>
                startTransition(async () => {
                  const response = await fetch(
                    `http://localhost:8000/api/accounts/${account.id}/mock-authorize`,
                    { method: "POST" },
                  );
                  const payload = await response.json();
                  setResult(JSON.stringify(payload, null, 2));
                })
              }
            >
              {pending ? "处理中..." : "标记为可发布"}
            </button>
          </div>
        ))}
      </div>
      {result ? <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{result}</pre> : null}
    </div>
  );
}

