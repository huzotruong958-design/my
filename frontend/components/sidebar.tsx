"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { Route } from "next";

const links: Array<{ href: Route; label: string }> = [
  { href: "/", label: "Dashboard" },
  { href: "/accounts", label: "公众号账号" },
  { href: "/jobs", label: "任务与产物" },
  { href: "/schedules", label: "定时计划" },
  { href: "/models", label: "模型配置" },
  { href: "/debug", label: "调试入口" },
  { href: "/login", label: "登录" },
];

export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="sidebar">
      <div className="stack">
        <div>
          <div className="eyebrow">WeChat Travel Agents</div>
          <h2 style={{ marginBottom: 8 }}>多 Agent 公众号后台</h2>
          <div className="muted">旅行攻略生成、授权绑定、定时发布与模型路由。</div>
        </div>
        <nav className="stack">
          {links.map(({ href, label }) => (
            <Link
              key={href}
              href={href}
              className="nav-link"
              data-active={pathname === href}
            >
              {label}
            </Link>
          ))}
        </nav>
      </div>
    </aside>
  );
}
