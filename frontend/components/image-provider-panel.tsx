"use client";

import { useState, useTransition } from "react";

import { apiGet, apiPatch } from "@/lib/api";

type ImageProviderStatus = {
  current_provider: string;
  available_providers: string[];
  uses_remote_download: boolean;
  uses_external_manifest?: boolean;
  uses_xiaohongshu_seed_urls?: boolean;
  uses_xiaohongshu_mcp?: boolean;
  uses_browser_automation?: boolean;
  playwright_available?: boolean;
  media_root: string;
  manifest_count?: number;
  manifest_preview?: ManifestItem[];
  xiaohongshu_seed_count?: number;
  xiaohongshu_seed_preview?: string[];
  xiaohongshu_mcp?: {
    enabled?: boolean;
    endpoint?: string;
    auth_header?: string;
    configured?: boolean;
    api_token_masked?: string;
    timeout_seconds?: number;
    last_probe?: Record<string, unknown>;
  };
};

type ManifestItem = {
  url: string;
  tag: string;
  title?: string;
  source_page?: string;
};

type ManifestResponse = {
  items: ManifestItem[];
  count?: number;
};

type SeedResponse = {
  urls: string[];
  count?: number;
};

export function ImageProviderPanel({
  status,
}: {
  status: ImageProviderStatus;
}) {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api";
  const [provider, setProvider] = useState(status.current_provider);
  const [savedStatus, setSavedStatus] = useState(status);
  const [xiaohongshuMcpEndpoint, setXiaohongshuMcpEndpoint] = useState(
    status.xiaohongshu_mcp?.endpoint ?? "",
  );
  const [xiaohongshuMcpToken, setXiaohongshuMcpToken] = useState("");
  const [xiaohongshuMcpAuthHeader, setXiaohongshuMcpAuthHeader] = useState(
    status.xiaohongshu_mcp?.auth_header ?? "Authorization",
  );
  const [xiaohongshuMcpEnabled, setXiaohongshuMcpEnabled] = useState(
    status.xiaohongshu_mcp?.enabled ?? false,
  );
  const [xiaohongshuMcpTimeout, setXiaohongshuMcpTimeout] = useState(
    String(status.xiaohongshu_mcp?.timeout_seconds ?? 30),
  );
  const [xiaohongshuSeeds, setXiaohongshuSeeds] = useState(
    JSON.stringify(
      [
        "https://www.xiaohongshu.com/explore/placeholder-note-1",
        "https://www.xiaohongshu.com/explore/placeholder-note-2",
      ],
      null,
      2,
    ),
  );
  const [manifestJson, setManifestJson] = useState(
    JSON.stringify(
      [
        {
          url: "https://picsum.photos/id/1018/1200/900",
          tag: "landmark",
          title: "示例主视觉",
          source_page: "manual-import",
        },
      ],
      null,
      2,
    ),
  );
  const [result, setResult] = useState("");
  const [pending, startTransition] = useTransition();

  async function saveProvider() {
    const payload = await apiPatch<ImageProviderStatus>("/search/image-providers", {
      provider,
    });
    setSavedStatus(payload);
    setProvider(payload.current_provider);
    setResult(JSON.stringify(payload, null, 2));
  }

  async function saveManifest() {
    const items = JSON.parse(manifestJson);
    const response = await fetch(`${apiUrl}/search/external-image-manifest`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ items }),
    });
    const payload: ManifestResponse = await response.json();
    setSavedStatus((current) => ({
      ...current,
      manifest_count: payload.count ?? payload.items.length,
      manifest_preview: payload.items.slice(0, 3),
    }));
    setResult(JSON.stringify(payload, null, 2));
  }

  async function loadManifest() {
    const payload = await apiGet<ManifestResponse>("/search/external-image-manifest");
    setManifestJson(JSON.stringify(payload.items, null, 2));
    setSavedStatus((current) => ({
      ...current,
      manifest_count: payload.items.length,
      manifest_preview: payload.items.slice(0, 3),
    }));
    setResult(JSON.stringify(payload, null, 2));
  }

  async function saveXiaohongshuSeeds() {
    const urls = JSON.parse(xiaohongshuSeeds);
    const response = await fetch(`${apiUrl}/search/xiaohongshu-seed-urls`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ urls }),
    });
    const payload: SeedResponse = await response.json();
    setSavedStatus((current) => ({
      ...current,
      xiaohongshu_seed_count: payload.count ?? payload.urls.length,
      xiaohongshu_seed_preview: payload.urls.slice(0, 3),
    }));
    setResult(JSON.stringify(payload, null, 2));
  }

  async function loadXiaohongshuSeeds() {
    const payload = await apiGet<SeedResponse>("/search/xiaohongshu-seed-urls");
    setXiaohongshuSeeds(JSON.stringify(payload.urls, null, 2));
    setSavedStatus((current) => ({
      ...current,
      xiaohongshu_seed_count: payload.count ?? payload.urls.length,
      xiaohongshu_seed_preview: payload.urls.slice(0, 3),
    }));
    setResult(JSON.stringify(payload, null, 2));
  }

  async function previewXiaohongshu() {
    const urls = JSON.parse(xiaohongshuSeeds);
    const response = await fetch(`${apiUrl}/search/xiaohongshu-preview`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        urls,
        destination: "自动发现旅行目的地",
        title: "旅行攻略自动配图",
        summary: "自动发现公开小红书笔记并抽取配图素材",
        limit: 8,
      }),
    });
    const payload = await response.json();
    setResult(JSON.stringify(payload, null, 2));
  }

  async function saveXiaohongshuMcpConfig() {
    const response = await fetch(`${apiUrl}/search/xiaohongshu-mcp-config`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        enabled: xiaohongshuMcpEnabled,
        endpoint: xiaohongshuMcpEndpoint,
        api_token: xiaohongshuMcpToken,
        auth_header: xiaohongshuMcpAuthHeader,
        timeout_seconds: Number(xiaohongshuMcpTimeout || 30),
      }),
    });
    const payload = await response.json();
    setSavedStatus((current) => ({
      ...current,
      xiaohongshu_mcp: payload,
    }));
    setResult(JSON.stringify(payload, null, 2));
  }

  async function probeXiaohongshuMcp() {
    const response = await fetch(`${apiUrl}/search/xiaohongshu-mcp-probe`, {
      method: "POST",
    });
    const payload = await response.json();
    setSavedStatus((current) => ({
      ...current,
      xiaohongshu_mcp: {
        ...(current.xiaohongshu_mcp ?? {}),
        last_probe: payload,
      },
    }));
    setResult(JSON.stringify(payload, null, 2));
  }

  return (
    <div className="panel stack">
      <div>
        <div className="eyebrow">Image Provider</div>
        <h3 style={{ marginBottom: 8 }}>图片来源切换</h3>
        <p className="muted">
          这里控制 `image_editor` 产物使用本地 SVG、远端示例图，或外部 URL 清单导入。
        </p>
      </div>
      <div className="grid">
        <label>
          当前 Provider
          <select value={provider} onChange={(event) => setProvider(event.target.value)}>
            {status.available_providers.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <div className="panel" style={{ padding: 16 }}>
          <div className="eyebrow">Media Root</div>
          <div className="muted">{status.media_root}</div>
        </div>
        <div className="panel" style={{ padding: 16 }}>
          <div className="eyebrow">Manifest Count</div>
          <div className="muted">{savedStatus.manifest_count ?? 0}</div>
        </div>
        <div className="panel" style={{ padding: 16 }}>
          <div className="eyebrow">XHS Seed Count</div>
          <div className="muted">{savedStatus.xiaohongshu_seed_count ?? 0}</div>
        </div>
      </div>
      <div style={{ display: "flex", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
        <button
          type="button"
          onClick={() => startTransition(async () => saveProvider())}
        >
          {pending ? "保存中..." : "保存图片 Provider"}
        </button>
        <span className="muted">
          当前模式：
          {savedStatus.uses_xiaohongshu_seed_urls
            ? "小红书自动搜索/公开页抽图"
            : savedStatus.uses_xiaohongshu_mcp
            ? "小红书 MCP 服务抽图"
            : savedStatus.uses_external_manifest
            ? "外部 URL 清单导入"
            : savedStatus.uses_remote_download
              ? "远端示例图下载"
              : "本地 SVG 生成"}
        </span>
        {savedStatus.uses_browser_automation ? (
          <span className="muted">
            浏览器自动化：
            {savedStatus.playwright_available ? "已启用" : "未安装"}
          </span>
        ) : null}
      </div>

      <div className="panel stack" style={{ padding: 16 }}>
        <div className="eyebrow">Xiaohongshu MCP</div>
        <p className="muted">
          优先接入外部 `xiaohongshu-mcp` 服务。首次登录由 MCP 服务自身持久化 cookie/会话，当前后台只保存服务入口、探活结果和登录状态检查结果。
        </p>
        <label>
          MCP Endpoint
          <input
            value={xiaohongshuMcpEndpoint}
            onChange={(event) => setXiaohongshuMcpEndpoint(event.target.value)}
            placeholder="http://127.0.0.1:8001/mcp"
          />
        </label>
        <label>
          API Token
          <input
            value={xiaohongshuMcpToken}
            onChange={(event) => setXiaohongshuMcpToken(event.target.value)}
            placeholder={savedStatus.xiaohongshu_mcp?.api_token_masked || "可选 Bearer Token"}
          />
        </label>
        <label>
          Auth Header
          <input
            value={xiaohongshuMcpAuthHeader}
            onChange={(event) => setXiaohongshuMcpAuthHeader(event.target.value)}
            placeholder="Authorization 或 X-API-Key"
          />
        </label>
        <label>
          Timeout Seconds
          <input
            value={xiaohongshuMcpTimeout}
            onChange={(event) => setXiaohongshuMcpTimeout(event.target.value)}
          />
        </label>
        <label style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <input
            type="checkbox"
            checked={xiaohongshuMcpEnabled}
            onChange={(event) => setXiaohongshuMcpEnabled(event.target.checked)}
          />
          启用 Xiaohongshu MCP 适配层
        </label>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <button
            type="button"
            className="secondary"
            onClick={() => startTransition(async () => saveXiaohongshuMcpConfig())}
          >
            {pending ? "处理中..." : "保存 MCP 配置"}
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() => startTransition(async () => probeXiaohongshuMcp())}
          >
            {pending ? "处理中..." : "探测登录/工具状态"}
          </button>
        </div>
        <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
          {JSON.stringify(savedStatus.xiaohongshu_mcp?.last_probe || {}, null, 2)}
        </pre>
      </div>

      <div className="panel stack" style={{ padding: 16 }}>
        <div className="eyebrow">Xiaohongshu Seeds</div>
        <p className="muted">
          当 provider 设为 `xiaohongshu-note-scrape` 时，系统会先用浏览器自动打开小红书搜索页抓取公开笔记；如果你额外保存了种子 URL，就优先从这些公开笔记页抽图。这个模式保留为本地 fallback。
        </p>
        <textarea
          rows={10}
          value={xiaohongshuSeeds}
          onChange={(event) => setXiaohongshuSeeds(event.target.value)}
        />
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <button
            type="button"
            className="secondary"
            onClick={() => startTransition(async () => loadXiaohongshuSeeds())}
          >
            {pending ? "处理中..." : "读取小红书种子"}
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() => startTransition(async () => saveXiaohongshuSeeds())}
          >
            {pending ? "处理中..." : "保存小红书种子"}
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() => startTransition(async () => previewXiaohongshu())}
          >
            {pending ? "处理中..." : "预览抽图结果"}
          </button>
        </div>
        <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
          {JSON.stringify(savedStatus.xiaohongshu_seed_preview || [], null, 2)}
        </pre>
      </div>

      <div className="panel stack" style={{ padding: 16 }}>
        <div className="eyebrow">External Manifest</div>
        <p className="muted">
          当 provider 设为 `external-url-ingest` 时，系统会下载这份清单里的图片并生成任务素材。
        </p>
        <textarea
          rows={14}
          value={manifestJson}
          onChange={(event) => setManifestJson(event.target.value)}
        />
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <button
            type="button"
            className="secondary"
            onClick={() => startTransition(async () => loadManifest())}
          >
            {pending ? "处理中..." : "读取清单"}
          </button>
          <button
            type="button"
            className="secondary"
            onClick={() => startTransition(async () => saveManifest())}
          >
            {pending ? "处理中..." : "保存清单"}
          </button>
        </div>
        <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
          {JSON.stringify(savedStatus.manifest_preview || [], null, 2)}
        </pre>
      </div>

      {result ? <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>{result}</pre> : null}
    </div>
  );
}
