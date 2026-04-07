import {
  JobDetail,
} from "@/components/job-detail-types";
import { JobArticleSection } from "@/components/job-article-section";
import { apiGet } from "@/lib/api";
import { JobImageSection } from "@/components/job-image-section";
import { JobMergedStateSection } from "@/components/job-merged-state-section";
import { JobOverviewCards } from "@/components/job-overview-cards";
import { JobPublishSection } from "@/components/job-publish-section";
import { JobTimelineSection } from "@/components/job-timeline-section";
import { resolveParsedOutputs } from "@/lib/job-detail";
import { PublishExecutePanel } from "@/components/publish-execute-panel";

export default async function JobDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const detail = await apiGet<JobDetail>(`/jobs/${id}`);
  const { writer, editor, formatter, facts, imageEditor } =
    resolveParsedOutputs(detail.parsed_output);

  return (
    <div className="stack">
      <div className="hero">
        <div className="eyebrow">Job Detail</div>
        <h1 style={{ margin: 0 }}>
          任务 #{detail.job.id} · {detail.job.destination || "待生成目的地"}
        </h1>
        <p className="muted">
          {detail.job.start_date} 至 {detail.job.end_date} · 当前状态 {detail.job.status}
        </p>
      </div>

      <JobOverviewCards
        detail={detail}
        finalTitle={editor?.result?.final_title || ""}
        summary={editor?.result?.summary || ""}
      />

      <JobArticleSection
        writer={writer}
        editor={editor}
        formatter={formatter}
        facts={facts}
      />

      <JobImageSection
        imageEditor={imageEditor}
        imageSourceSummary={detail.image_source_summary}
        mediaAssets={detail.media_assets}
      />

      <JobPublishSection
        publishPreview={detail.publish_preview}
        publishResult={detail.publish_result}
        publishRecord={detail.publish_record}
      />

      <JobTimelineSection jobId={detail.job.id} steps={detail.steps} />

      <PublishExecutePanel jobId={detail.job.id} />

      <JobMergedStateSection parsedOutput={detail.parsed_output} />
    </div>
  );
}
