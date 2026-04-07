"use client";

type AccountsAuthLaunchProps = {
  authorizationUrl: string;
};

export function AccountsAuthLaunch({ authorizationUrl }: AccountsAuthLaunchProps) {
  return (
    <div className="panel stack">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
        <div>
          <h3 style={{ marginTop: 0 }}>发起公众号授权</h3>
          <p className="muted">
            授权成功后，账号状态会变成可发布，定时任务才可启用。未配置真实 component
            凭据时，下面仍可走本地 mock 联调。
          </p>
        </div>
        <a className="button" href={authorizationUrl}>
          去微信授权
        </a>
      </div>
    </div>
  );
}
