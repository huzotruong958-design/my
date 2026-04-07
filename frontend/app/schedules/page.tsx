import { apiGet } from "@/lib/api";
import { CreateScheduleForm } from "@/components/create-schedule-form";
import { PageHero } from "@/components/page-hero";
import { ScheduleActions } from "@/components/schedule-actions";
import { ScheduleEditPanel } from "@/components/schedule-edit-panel";
import { SchedulesTable } from "@/components/schedules-table";

export default async function SchedulesPage() {
  const schedules = await apiGet<any[]>("/schedules");
  return (
    <div className="stack">
      <PageHero
        eyebrow="Schedules"
        title="按公众号独立配置定时发布"
        description="支持 cron、时区、时间窗和开关。只有已授权账号能启用计划。"
      />
      <CreateScheduleForm />
      <ScheduleEditPanel schedules={schedules} />
      <ScheduleActions schedules={schedules} />
      <SchedulesTable schedules={schedules} />
    </div>
  );
}
