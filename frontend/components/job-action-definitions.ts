"use client";

import {
  summarizePublishAction,
  summarizeRefreshImagesAction,
  summarizeReplayAction,
} from "@/components/job-action-summary";
import { JobActionOptions } from "@/components/job-action-types";

export function buildReplayAction(jobId: number): JobActionOptions {
  return {
    path: `/jobs/${jobId}/replay`,
    init: {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({}),
    },
    summarize: summarizeReplayAction,
  };
}

export function buildRefreshImagesAction(jobId: number): JobActionOptions {
  return {
    path: `/jobs/${jobId}/refresh-images`,
    init: {
      method: "POST",
    },
    summarize: summarizeRefreshImagesAction,
  };
}

export function buildPublishAction(jobId: number, dryRun: boolean): JobActionOptions {
  return {
    path: `/jobs/${jobId}/publish-execute`,
    init: {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ dry_run: dryRun }),
    },
    summarize: summarizePublishAction,
  };
}
