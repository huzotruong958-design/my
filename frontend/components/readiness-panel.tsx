type ReadinessProps = {
  accounts: any[];
  jobs: any[];
  schedules: any[];
  modelReadiness: {
    tenant_id: number;
    credential_count: number;
    validated_credentials: number;
    configured_agents: string[];
    ready_for_real_llm: boolean;
  };
  wechatConfig: {
    ready_for_real_auth: boolean;
    callback_base_url: string;
  };
  imageProvider: {
    current_provider: string;
    available_providers: string[];
    uses_remote_download: boolean;
    media_root: string;
  };
};

export function ReadinessPanel({
  accounts,
  jobs,
  schedules,
  modelReadiness,
  wechatConfig,
  imageProvider,
}: ReadinessProps) {
  const publishableAccounts = accounts.filter((item) => item.publishable).length;
  const schedulesWithRuntime = schedules.filter((item) => item.next_run_time || item.last_run).length;

  return (
    <section className="panel stack">
      <div>
        <div className="eyebrow">Readiness</div>
        <h2 style={{ marginBottom: 8 }}>联调总览</h2>
        <p className="muted">这里把模型、公众号授权和调度状态汇总到一起，先判断当前环境差哪一块。</p>
      </div>
      <div className="grid">
        <article className="panel" style={{ padding: 16 }}>
          <div className="eyebrow">LLM</div>
          <h3>{String(modelReadiness.ready_for_real_llm)}</h3>
          <div className="muted">
            凭据 {modelReadiness.validated_credentials}/{modelReadiness.credential_count} 已验证
          </div>
        </article>
        <article className="panel" style={{ padding: 16 }}>
          <div className="eyebrow">WeChat Auth</div>
          <h3>{String(wechatConfig.ready_for_real_auth)}</h3>
          <div className="muted">回调地址：{wechatConfig.callback_base_url}</div>
        </article>
        <article className="panel" style={{ padding: 16 }}>
          <div className="eyebrow">Publishable Accounts</div>
          <h3>{publishableAccounts}</h3>
          <div className="muted">可发布公众号 / 总账号 {accounts.length}</div>
        </article>
        <article className="panel" style={{ padding: 16 }}>
          <div className="eyebrow">Scheduler</div>
          <h3>{schedulesWithRuntime}</h3>
          <div className="muted">已具备运行信息的计划 / 总计划 {schedules.length}</div>
        </article>
        <article className="panel" style={{ padding: 16 }}>
          <div className="eyebrow">Image Provider</div>
          <h3>{imageProvider.current_provider}</h3>
          <div className="muted">
            {imageProvider.uses_remote_download ? "远端示例图下载" : "本地 SVG 素材生成"}
          </div>
        </article>
      </div>
      <div className="grid">
        <div className="panel" style={{ padding: 16 }}>
          <div className="eyebrow">Configured Agents</div>
          <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
            {JSON.stringify(modelReadiness.configured_agents, null, 2)}
          </pre>
        </div>
        <div className="panel" style={{ padding: 16 }}>
          <div className="eyebrow">Job Count</div>
          <h3>{jobs.length}</h3>
          <div className="muted">已经生成的文章任务数量</div>
        </div>
        <div className="panel" style={{ padding: 16 }}>
          <div className="eyebrow">Image Providers</div>
          <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
            {JSON.stringify(imageProvider.available_providers, null, 2)}
          </pre>
        </div>
      </div>
    </section>
  );
}
