import {
  ParsedJobOutputs,
  PublishPreviewDetail,
} from "@/components/job-detail-types";

export const agentLabels: Record<string, string> = {
  researcher: "素材采集者",
  fact_checker: "信息校验者",
  writer: "文章撰写者",
  formatter: "格式校准者",
  editor: "编辑 Agent",
  image_editor: "图片编辑 Agent",
  publisher: "文章发布者",
};

export function prettyJson(value: unknown) {
  try {
    if (typeof value === "string") {
      return JSON.stringify(JSON.parse(value), null, 2);
    }
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

export function executionModeLabel(mode: string | undefined) {
  if (mode === "llm") return "真实 LLM";
  if (mode === "mock_fallback") return "回退到 Mock";
  return "Mock 占位";
}

export function agentLabel(agentName: string | undefined) {
  if (!agentName) return "未开始";
  return agentLabels[agentName] ?? agentName;
}

export function formatDuration(seconds: number | null | undefined) {
  if (seconds == null) return "-";
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (minutes < 60) return `${minutes}m ${remainingSeconds}s`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return `${hours}h ${remainingMinutes}m`;
}

export function resolvePublishPreview(preview: PublishPreviewDetail | undefined) {
  return {
    publishReadiness: preview?.publish_readiness ?? {},
    publishPayload: preview?.publish_payload ?? {},
    publishBundle: preview?.publish_bundle ?? {},
    authorizationContext: preview?.authorization_context ?? {},
  };
}

export function resolveParsedOutputs(parsedOutput: ParsedJobOutputs | undefined) {
  return {
    writer: parsedOutput?.writer,
    editor: parsedOutput?.editor,
    formatter: parsedOutput?.formatter,
    facts: parsedOutput?.fact_checker,
    imageEditor: parsedOutput?.image_editor,
  };
}
