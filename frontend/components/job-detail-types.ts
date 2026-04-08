"use client";

export type JobStepDetail = {
  id: number;
  agent_name: string;
  status: string;
  model_provider: string;
  model_name: string;
  output_json: string;
};

export type PublishRecordDetail = {
  authorization_mode: string;
  draft_id: string;
  cover_media_id: string;
  content_media_ids: string;
  content_media_ids_parsed: string[];
  thumb_result: Record<string, unknown>;
  upload_results: Array<Record<string, unknown>>;
  draft_response: Record<string, unknown>;
  raw_response: string;
};

export type PublishPreviewDetail = {
  authorization_mode: string;
  authorization_context: Record<string, unknown>;
  publish_payload: Record<string, unknown>;
  publish_bundle: {
    thumb_request?: Record<string, unknown>;
    upload_requests?: Array<Record<string, unknown>>;
    draft_request?: Record<string, unknown>;
  };
  publish_readiness: {
    publish_ready?: boolean;
    missing_assets?: string[];
    dry_run_recommended?: boolean;
    authorization_mode_hint?: string;
    required_actions?: string[];
  };
};

export type MediaAssetDetail = {
  id: number;
  asset_type: string;
  source_url: string;
  local_path: string;
  upload_role: string;
  wechat_media_id: string;
  wechat_url: string;
  metadata_json: string;
  metadata: Record<string, unknown>;
  upload_response: Record<string, unknown>;
  media_url: string;
};

export type ImageSourceSummary = {
  providers: string[];
  tags: string[];
  source_pages: string[];
  asset_count: number;
};

export type WriterOutput = {
  result?: {
    title_candidates?: string[];
    body?: string;
    closing?: string;
  };
};

export type EditorOutput = {
  result?: {
    final_title?: string;
    summary?: string;
    cover_caption?: string;
  };
};

export type FormatterOutput = {
  result?: {
    formatted_body?: string;
    image_slots?: string[];
  };
};

export type FactCheckerOutput = {
  result?: {
    facts_summary?: Record<string, unknown>;
  };
};

export type ImageEditorOutput = {
  result?: {
    image_asset_pack?: Record<string, unknown>;
    provider_context?: Record<string, unknown>;
    cover_strategy?: Record<string, unknown>;
    required_tags?: string[];
    collage_plan?: string;
    selection_notes?: string[];
    slot_assignments?: Array<Record<string, unknown>>;
  };
};

export type ParsedJobOutputs = {
  writer?: WriterOutput;
  editor?: EditorOutput;
  formatter?: FormatterOutput;
  fact_checker?: FactCheckerOutput;
  image_editor?: ImageEditorOutput;
};

export type JobTimingDetail = {
  started_at: string;
  last_event_at: string;
  finished_at: string;
  running_seconds: number;
  completed_seconds: number | null;
  current_step: string;
  current_step_status: string;
  next_step: string;
  completed_step_count: number;
  total_step_count: number;
};

export type JobDetail = {
  job: {
    id: number;
    destination: string;
    start_date: string;
    end_date: string;
    status: string;
    error_message?: string;
  };
  timing: JobTimingDetail;
  steps: JobStepDetail[];
  publish_record: PublishRecordDetail | null;
  publish_result: Record<string, unknown>;
  publish_preview: PublishPreviewDetail;
  media_assets: MediaAssetDetail[];
  image_source_summary: ImageSourceSummary;
  parsed_output: ParsedJobOutputs & Record<string, unknown>;
};
