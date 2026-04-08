import { apiGet } from "@/lib/api";
import { ModelControlCenter } from "@/components/model-control-center";
import { ModelProviderGrid } from "@/components/model-provider-grid";
import { PageHero } from "@/components/page-hero";

export default async function ModelsPage() {
  const [providers, configs, credentials, contentStrategy] = await Promise.all([
    apiGet<any[]>("/models/providers"),
    apiGet<any[]>("/models/tenants/1/agent-configs"),
    apiGet<any[]>("/models/tenants/1/credentials"),
    apiGet<any>("/models/content-strategy"),
  ]);
  return (
    <div className="stack">
      <PageHero
        eyebrow="Routing"
        title="按 Agent 配置不同模型"
        description="每个租户可以把写作者、校验者、图片 Agent 路由到不同 provider/model。"
      />
      <ModelProviderGrid providers={providers} />
      <ModelControlCenter
        providers={providers}
        credentials={credentials}
        configs={configs}
        contentStrategy={contentStrategy}
      />
    </div>
  );
}
