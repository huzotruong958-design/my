from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


def create_db_and_tables() -> None:
    from app.models.entities import (  # noqa: F401
        AppSetting,
        AgentModelConfig,
        ArticleJob,
        JobStep,
        MediaAsset,
        ModelCredential,
        OfficialAccount,
        PublishRecord,
        Schedule,
        ScheduleRun,
        Tenant,
        User,
        WeChatAuthorization,
    )

    SQLModel.metadata.create_all(engine)
    _ensure_sqlite_compat_columns()


def _ensure_sqlite_compat_columns() -> None:
    if not settings.database_url.startswith("sqlite"):
        return
    column_specs: dict[str, dict[str, str]] = {
        "mediaasset": {
            "upload_role": "TEXT NOT NULL DEFAULT ''",
            "wechat_media_id": "TEXT NOT NULL DEFAULT ''",
            "wechat_url": "TEXT NOT NULL DEFAULT ''",
            "upload_response_json": "TEXT NOT NULL DEFAULT '{}'",
        },
        "publishrecord": {
            "authorization_mode": "TEXT NOT NULL DEFAULT ''",
            "thumb_result_json": "TEXT NOT NULL DEFAULT '{}'",
            "upload_results_json": "TEXT NOT NULL DEFAULT '[]'",
            "draft_response_json": "TEXT NOT NULL DEFAULT '{}'",
        },
    }
    with engine.begin() as connection:
        inspector = inspect(connection)
        table_names = set(inspector.get_table_names())
        for table_name, specs in column_specs.items():
            if table_name not in table_names:
                continue
            existing = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, ddl in specs.items():
                if column_name in existing:
                    continue
                connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}"))


def get_session():
    with Session(engine) as session:
        yield session
