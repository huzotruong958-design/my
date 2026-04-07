import { apiGet, apiPost } from "@/lib/api";
import { AccountsAuthLaunch } from "@/components/accounts-auth-launch";
import { AccountPublishContext } from "@/components/account-publish-context";
import { AccountStatusActions } from "@/components/account-status-actions";
import { AccountsTable } from "@/components/accounts-table";
import { AccountTestActions } from "@/components/account-test-actions";
import { PageHero } from "@/components/page-hero";
import { WeChatConfigPanel } from "@/components/wechat-config-panel";

export default async function AccountsPage() {
  const accounts = await apiGet<any[]>("/accounts");
  const publishContexts = await Promise.all(
    accounts.map((account) => apiGet<any>(`/accounts/${account.id}/publish-context`)),
  );
  const auth = await apiPost<{ authorization_url: string; binding_guide: any }>(
    "/accounts/wechat/auth/start?tenant_id=1",
  );
  const config = await apiGet<any>("/accounts/wechat/config-status");

  return (
    <div className="stack">
      <PageHero
        eyebrow="Accounts"
        title="公众号授权绑定"
        description="后台用户先登录系统，再发起第三方平台授权绑定公众号。"
      />
      <AccountsAuthLaunch authorizationUrl={auth.authorization_url} />
      <WeChatConfigPanel config={config} guide={auth.binding_guide} />
      <AccountsTable accounts={accounts} />
      <AccountTestActions accounts={accounts} />
      <AccountStatusActions accounts={accounts} />
      <AccountPublishContext contexts={publishContexts} />
    </div>
  );
}
