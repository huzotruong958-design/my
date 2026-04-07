"use client";

import {
  EditorOutput,
  FactCheckerOutput,
  FormatterOutput,
  WriterOutput,
} from "@/components/job-detail-types";
import { prettyJson } from "@/lib/job-detail";

type JobArticleSectionProps = {
  writer?: WriterOutput;
  editor?: EditorOutput;
  formatter?: FormatterOutput;
  facts?: FactCheckerOutput;
};

export function JobArticleSection({
  writer,
  editor,
  formatter,
  facts,
}: JobArticleSectionProps) {
  return (
    <div className="grid">
      <div className="panel stack">
        <div className="eyebrow">Article Preview</div>
        <h3 style={{ marginTop: 0 }}>{editor?.result?.final_title || "正文预览"}</h3>
        <div className="muted">{editor?.result?.cover_caption || "暂无封面文案"}</div>
        <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
          {formatter?.result?.formatted_body || writer?.result?.body || "暂无正文"}
        </pre>
      </div>
      <div className="panel stack">
        <div className="eyebrow">Facts Summary</div>
        <h3 style={{ marginTop: 0 }}>校验后的干货模块</h3>
        <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
          {prettyJson(facts?.result?.facts_summary || {})}
        </pre>
        <div className="eyebrow">Title Candidates</div>
        <pre style={{ whiteSpace: "pre-wrap", margin: 0 }}>
          {prettyJson(writer?.result?.title_candidates || [])}
        </pre>
      </div>
    </div>
  );
}
