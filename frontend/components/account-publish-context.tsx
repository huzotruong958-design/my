type PublishContext = {
  account_id: number;
  display_name: string;
  publishable: boolean;
  authorization_mode: string;
  authorization?: {
    authorizer_app_id?: string;
    expires_at?: string;
    updated_at?: string;
    has_refresh_token?: boolean;
  } | null;
  refresh_request_preview?: Record<string, unknown> | null;
};

export function AccountPublishContext({
  contexts,
}: {
  contexts: PublishContext[];
}) {
  return (
    <div className="panel stack">
      <div>
        <div className="eyebrow">Publish Context</div>
        <h3 style={{ marginBottom: 8 }}>公众号发布诊断</h3>
        <p className="muted">这里展示每个公众号当前走 mock 还是第三方平台授权，以及 token 刷新请求预览。</p>
      </div>
      <div className="stack">
        {contexts.map((item) => (
          <div key={item.account_id} className="panel stack" style={{ padding: 16 }}>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
              <div>
                <div className="eyebrow">{item.authorization_mode}</div>
                <strong>{item.display_name}</strong>
              </div>
              <div className="muted">{item.publishable ? "可发布" : "不可发布"}</div>
            </div>
            <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
              {JSON.stringify(item.authorization || {}, null, 2)}
            </pre>
            <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
              {JSON.stringify(item.refresh_request_preview || {}, null, 2)}
            </pre>
          </div>
        ))}
      </div>
    </div>
  );
}
