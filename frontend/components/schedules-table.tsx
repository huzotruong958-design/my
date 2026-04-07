"use client";

import { ScheduleRow } from "@/components/admin-page-types";

export function SchedulesTable({ schedules }: { schedules: ScheduleRow[] }) {
  return (
    <div className="panel">
      <table>
        <thead>
          <tr>
            <th>名称</th>
            <th>Cron</th>
            <th>时区</th>
            <th>时间窗</th>
            <th>启用</th>
            <th>下次执行</th>
            <th>最近运行</th>
          </tr>
        </thead>
        <tbody>
          {schedules.map((schedule) => (
            <tr key={schedule.id}>
              <td>{schedule.name}</td>
              <td>{schedule.cron}</td>
              <td>{schedule.timezone}</td>
              <td>
                {schedule.time_window_start} - {schedule.time_window_end}
              </td>
              <td>{String(schedule.enabled)}</td>
              <td>{schedule.next_run_time || "-"}</td>
              <td>
                {schedule.last_run
                  ? `${schedule.last_run.status} / attempt ${schedule.last_run.attempt} / ${schedule.last_run.message}`
                  : "-"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
