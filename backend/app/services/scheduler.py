from __future__ import annotations

import json
from datetime import date, datetime, time, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, select

from app.db.session import create_db_and_tables, engine
from app.models.entities import (
    ArticleJob,
    JobStatus,
    OfficialAccount,
    Schedule,
    ScheduleRun,
)
from app.schemas.common import TravelRequest
from app.services.workflow import workflow_service


class SchedulerService:
    def __init__(self) -> None:
        self._scheduler = BackgroundScheduler()
        self._started = False
        self.default_retry_limit = 2

    def start(self) -> None:
        if not self._started:
            self._scheduler.start()
            self._started = True
            self.sync_all()

    def shutdown(self) -> None:
        if self._started:
            self._scheduler.shutdown(wait=False)
            self._started = False

    def sync_all(self) -> None:
        with Session(engine) as session:
            schedules = session.exec(select(Schedule)).all()
            for schedule in schedules:
                self.register_schedule(schedule)

    def register_schedule(self, schedule: Schedule) -> None:
        job_id = self._job_id(schedule.id or 0)
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
        if not schedule.enabled:
            return
        trigger = CronTrigger.from_crontab(schedule.cron, timezone=schedule.timezone)
        self._scheduler.add_job(
            self.run_scheduled_job,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            kwargs={"schedule_id": schedule.id, "trigger_type": "cron"},
        )

    def run_scheduled_job(self, schedule_id: int, trigger_type: str = "cron") -> None:
        with Session(engine) as session:
            schedule = session.get(Schedule, schedule_id)
            if not schedule or not schedule.enabled:
                return
            account = session.get(OfficialAccount, schedule.official_account_id)
            if not account or not account.publishable:
                self._record_run(
                    session, schedule_id, trigger_type, 1, "skipped", "Official account is not publishable."
                )
                return
            if not self._is_within_window(schedule.time_window_start, schedule.time_window_end):
                self._record_run(
                    session,
                    schedule_id,
                    trigger_type,
                    1,
                    "skipped",
                    f"Current time is outside window {schedule.time_window_start}-{schedule.time_window_end}.",
                )
                return

            today = date.today()
            payload = TravelRequest(
                tenant_id=schedule.tenant_id,
                account_id=schedule.official_account_id,
                start_date=today.isoformat(),
                end_date=(today + timedelta(days=2)).isoformat(),
                audience_profile="定时任务自动生成",
                style_preset="克制、有画面感",
                extra_constraints=(
                    f"由计划 {schedule.name} 触发，需符合时间窗 "
                    f"{schedule.time_window_start}-{schedule.time_window_end}"
                ),
            )
            last_error = ""
            for attempt in range(1, self.default_retry_limit + 2):
                article_job = workflow_service.create_job(session, payload)
                article_job.schedule_id = schedule.id
                session.add(article_job)
                session.commit()
                session.refresh(article_job)
                workflow_service.run_job(session, article_job)
                if article_job.status == JobStatus.succeeded:
                    self._record_run(
                        session,
                        schedule.id or 0,
                        trigger_type,
                        attempt,
                        "succeeded",
                        "Workflow completed successfully.",
                        article_job.id,
                    )
                    return
                last_error = article_job.error_message or "Workflow failed without explicit error."
                self._record_run(
                    session,
                    schedule.id or 0,
                    trigger_type,
                    attempt,
                    "failed",
                    last_error,
                    article_job.id,
                )
            self._record_run(
                session,
                schedule.id or 0,
                trigger_type,
                self.default_retry_limit + 1,
                "exhausted",
                f"Retry limit reached. Last error: {last_error}",
            )

    def replay_job(self, article_job_id: int) -> ArticleJob | None:
        with Session(engine) as session:
            original = session.get(ArticleJob, article_job_id)
            if not original:
                return None
            payload = TravelRequest.model_validate(json.loads(original.payload_json))
            replay = workflow_service.create_job(session, payload)
            replay.schedule_id = original.schedule_id
            session.add(replay)
            session.commit()
            session.refresh(replay)
            return workflow_service.run_job(session, replay)

    def list_schedule_runtime(self) -> list[dict]:
        with Session(engine) as session:
            schedules = session.exec(select(Schedule).order_by(Schedule.id.desc())).all()
            latest_runs: dict[int, ScheduleRun] = {}
            try:
                for item in session.exec(select(ScheduleRun).order_by(ScheduleRun.id.desc())).all():
                    if item.schedule_id not in latest_runs:
                        latest_runs[item.schedule_id] = item
            except OperationalError:
                create_db_and_tables()
            result = []
            for schedule in schedules:
                runtime_job = self._scheduler.get_job(self._job_id(schedule.id or 0))
                latest = latest_runs.get(schedule.id or 0)
                result.append(
                    {
                        "id": schedule.id,
                        "tenant_id": schedule.tenant_id,
                        "official_account_id": schedule.official_account_id,
                        "name": schedule.name,
                        "cron": schedule.cron,
                        "timezone": schedule.timezone,
                        "time_window_start": schedule.time_window_start,
                        "time_window_end": schedule.time_window_end,
                        "enabled": schedule.enabled,
                        "next_run_time": runtime_job.next_run_time.isoformat()
                        if runtime_job and runtime_job.next_run_time
                        else None,
                        "last_run": {
                            "status": latest.status,
                            "message": latest.message,
                            "attempt": latest.attempt,
                            "created_at": latest.created_at.isoformat(),
                            "article_job_id": latest.article_job_id,
                            "trigger_type": latest.trigger_type,
                        }
                        if latest
                        else None,
                    }
                )
            return result

    def _record_run(
        self,
        session: Session,
        schedule_id: int,
        trigger_type: str,
        attempt: int,
        status: str,
        message: str,
        article_job_id: int | None = None,
    ) -> None:
        create_db_and_tables()
        session.add(
            ScheduleRun(
                schedule_id=schedule_id,
                article_job_id=article_job_id,
                trigger_type=trigger_type,
                attempt=attempt,
                status=status,
                message=message,
            )
        )
        session.commit()

    def _is_within_window(self, start: str, end: str) -> bool:
        now = datetime.now().time()
        start_time = time.fromisoformat(start)
        end_time = time.fromisoformat(end)
        if start_time <= end_time:
            return start_time <= now <= end_time
        return now >= start_time or now <= end_time

    def _job_id(self, schedule_id: int) -> str:
        return f"schedule:{schedule_id}"


scheduler_service = SchedulerService()
