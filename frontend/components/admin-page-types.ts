"use client";

export type AccountRow = {
  id: number;
  display_name: string;
  wechat_app_id: string;
  status: string;
  last_refreshed_at?: string | null;
  authorization?: {
    expires_at?: string | null;
  };
};

export type ScheduleRow = {
  id: number;
  name: string;
  cron: string;
  timezone: string;
  time_window_start: string;
  time_window_end: string;
  enabled: boolean;
  next_run_time?: string | null;
  last_run?: {
    status: string;
    attempt: number;
    message: string;
  } | null;
};
