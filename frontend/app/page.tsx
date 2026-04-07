import { apiGet } from "@/lib/api";
import { ImageProviderPanel } from "@/components/image-provider-panel";
import { ReadinessPanel } from "@/components/readiness-panel";

export default async function DashboardPage() {
  const [accounts, jobs, schedules, modelReadiness, wechatConfig, imageProvider] = await Promise.all([
    apiGet<any[]>("/accounts"),
    apiGet<any[]>("/jobs"),
    apiGet<any[]>("/schedules"),
    apiGet<any>("/models/tenants/1/readiness"),
    apiGet<any>("/accounts/wechat/config-status"),
    apiGet<any>("/search/image-providers"),
  ]);

  return (
    <div className="stack">
      <section className="hero">
        <div className="eyebrow">Overview</div>
        <h1 style={{ margin: 0 }}>发布、生成和调度都在一个后台里完成</h1>
        <p className="muted">
          这里是首版运营台：绑定公众号授权、配置 Agent 模型、发起旅行攻略任务，并自动写入公众号草稿箱。
        </p>
      </section>
      <section className="grid">
        <article className="panel">
          <div className="eyebrow">Accounts</div>
          <h2>{accounts.length}</h2>
          <div className="muted">已绑定公众号</div>
        </article>
        <article className="panel">
          <div className="eyebrow">Jobs</div>
          <h2>{jobs.length}</h2>
          <div className="muted">生成任务总数</div>
        </article>
        <article className="panel">
          <div className="eyebrow">Schedules</div>
          <h2>{schedules.length}</h2>
          <div className="muted">已配置定时计划</div>
        </article>
      </section>
      <ReadinessPanel
        accounts={accounts}
        jobs={jobs}
        schedules={schedules}
        modelReadiness={modelReadiness}
        wechatConfig={wechatConfig}
        imageProvider={imageProvider}
      />
      <ImageProviderPanel status={imageProvider} />
    </div>
  );
}
