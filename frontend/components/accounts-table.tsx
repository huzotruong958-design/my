"use client";

import { AccountRow } from "@/components/admin-page-types";

export function AccountsTable({ accounts }: { accounts: AccountRow[] }) {
  return (
    <div className="panel">
      <table>
        <thead>
          <tr>
            <th>名称</th>
            <th>App ID</th>
            <th>状态</th>
            <th>最后刷新</th>
            <th>授权信息</th>
          </tr>
        </thead>
        <tbody>
          {accounts.map((account) => (
            <tr key={account.id}>
              <td>{account.display_name}</td>
              <td>{account.wechat_app_id}</td>
              <td>{account.status}</td>
              <td>{account.last_refreshed_at ?? "-"}</td>
              <td>{account.authorization?.expires_at ? `expires ${account.authorization.expires_at}` : "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
