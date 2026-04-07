"use client";

import { JobActionResponse } from "@/components/job-action-types";

export function summarizeReplayAction(payload: JobActionResponse): string {
  const replayJobId = payload?.job?.id || "";
  const replayStatus = payload?.job?.status || "-";
  return `mode=${payload?.mode || "-"} · job=${replayJobId || "未知"} · status=${replayStatus}`;
}

export function summarizeRefreshImagesAction(payload: JobActionResponse): string {
  const provider = payload?.image_asset_pack?.provider || "-";
  const imageCount = Array.isArray(payload?.image_asset_pack?.images)
    ? payload.image_asset_pack.images.length
    : 0;
  return `mode=${payload?.mode || "-"} · provider=${provider} · images=${imageCount}`;
}

export function summarizePublishAction(payload: JobActionResponse): string {
  const publishResult = payload?.publish_result || {};
  const draftId =
    payload?.publish_record?.draft_id ||
    (typeof publishResult?.draft_id === "string" ? publishResult.draft_id : "") ||
    "";
  const authorizationMode =
    payload?.publish_preview?.authorization_mode || payload?.authorization_mode || "-";
  return `mode=${payload?.mode || "-"} · auth=${authorizationMode} · draft=${draftId || "未生成"}`;
}
