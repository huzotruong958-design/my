"use client";

export type PublishRecordLike = {
  draft_id?: string;
};

export type PublishPreviewLike = {
  authorization_mode?: string;
};

export type ReplayJobLike = {
  id?: number;
  status?: string;
};

export type ImageAssetPackLike = {
  provider?: string;
  images?: unknown[];
};

export type JobActionResponse = {
  ok?: boolean;
  mode?: string;
  authorization_mode?: string;
  job?: ReplayJobLike;
  publish_record?: PublishRecordLike | null;
  publish_result?: Record<string, unknown>;
  publish_preview?: PublishPreviewLike;
  image_asset_pack?: ImageAssetPackLike;
};

export type JobActionSummaryFn<T extends JobActionResponse = JobActionResponse> = (payload: T) => string;

export type JobActionOptions<T extends JobActionResponse = JobActionResponse> = {
  path: string;
  init?: RequestInit;
  summarize: JobActionSummaryFn<T>;
};
