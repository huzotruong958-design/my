import Link from "next/link";

import { apiGet } from "@/lib/api";
import { CreateJobForm } from "@/components/create-job-form";

export default async function JobsPage() {
  const jobs = await apiGet<any[]>("/jobs");
  return (
    <div className="stack">
      <div className="hero">
        <div className="eyebrow">Jobs</div>
        <h1 style={{ margin: 0 }}>任务与 Agent 产物</h1>
        <p className="muted">查看生成结果、发布状态，以及每个 Agent 实际使用的模型。</p>
      </div>
      <CreateJobForm />
      {jobs.length === 0 ? (
        <div className="panel muted">当前还没有任务。调用后端 `/api/jobs/travel/generate-and-publish` 即可生成首条记录。</div>
      ) : (
        jobs.map((job) => (
          <div key={job.id} className="panel stack">
            <div style={{ display: "flex", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
              <div>
                <div className="eyebrow">Job #{job.id}</div>
                <h3 style={{ marginTop: 6 }}>{job.destination || "待生成目的地"}</h3>
              </div>
              <div className="muted">{job.status}</div>
            </div>
            <div className="muted">
              {job.start_date} 至 {job.end_date}
            </div>
            <div>
              <Link className="button secondary" href={`/jobs/${job.id}`}>
                查看执行详情
              </Link>
            </div>
          </div>
        ))
      )}
    </div>
  );
}
