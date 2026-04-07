"use client";

import { useState, useTransition } from "react";

type Account = {
  id: number;
  display_name: string;
  wechat_app_id: string;
  status: string;
  last_refreshed_at?: string | null;
};

export function AccountStatusActions({ accounts }: { accounts: Account[] }) {
  const [result, setResult] = useState("");
  const [pending, startTransition] = useTransition();

  return (
    <div className="panel stack">
      <div>
        <div className="eyebrow">Refresh</div>
        <h3 style={{ marginBottom: 8 }}>刷新公众号授权状态</h3>
        <p className="muted">当微信授权临近过期或状态异常时，可以在后台手动触发一次状态刷新。</p>
      </div>
      <div className="stack">
        {accounts.length === 0 ? (
          <div className="muted">当前还没有公众号账号。</div>
        ) : (
          accounts.map((account) => (
            <div
              key={account.id}
              className="panel"
              style={{ padding: 16, display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}
            >
              <div>
                <div className="eyebrow">{account.wechat_app_id}</div>
                <strong>{account.display_name}</strong>
                <div className="muted">
                  状态：{account.status} · 最近刷新：{account.last_refreshed_at ?? "-"}
                </div>
              </div>
              <button
                type="button"
                onClick={() =>
                  startTransition(async () => {
                    const response = await fetch(
                      `http://localhost:8000/api/accounts/${account.id}/refresh-status`,
                      {
                        method: "POST",
                      },
                    );
                    const payload = await response.json();
                    setResult(JSON.stringify(payload, null, 2));
                  })
                }
              >
                {pending ? "刷新中..." : "刷新状态"}
              </button>
            </div>
          ))
        )}
      </div>
      {result ? <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{result}</pre> : null}
    </div>
  );
}

