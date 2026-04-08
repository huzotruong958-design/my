"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const ACTIVE_JOB_STATUSES = new Set(["pending", "running"]);
const POLL_INTERVAL_MS = 5000;

type JobDetailAutoRefreshProps = {
  status: string;
  children: React.ReactNode;
};

export function JobDetailAutoRefresh({
  status,
  children,
}: JobDetailAutoRefreshProps) {
  const router = useRouter();
  const [lastRefreshAt, setLastRefreshAt] = useState(() => new Date());
  const isActive = ACTIVE_JOB_STATUSES.has(status);

  useEffect(() => {
    if (!isActive) {
      return;
    }
    const timer = window.setTimeout(() => {
      setLastRefreshAt(new Date());
      router.refresh();
    }, POLL_INTERVAL_MS);
    return () => window.clearTimeout(timer);
  }, [isActive, lastRefreshAt, router]);

  return (
    <div className="stack">
      {isActive ? (
        <div className="panel muted" style={{ padding: "12px 16px" }}>
          任务仍在运行，页面每 5 秒自动刷新一次。最近触发时间{" "}
          {lastRefreshAt.toLocaleTimeString("zh-CN", { hour12: false })}
        </div>
      ) : null}
      {children}
    </div>
  );
}
