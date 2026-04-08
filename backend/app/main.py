from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings
from app.db.session import create_db_and_tables
from app.services.scheduler import scheduler_service
from app.services.workflow import workflow_service


@asynccontextmanager
async def lifespan(_: FastAPI):
    create_db_and_tables()
    workflow_service.reconcile_stale_running_jobs()
    scheduler_service.start()
    yield
    scheduler_service.shutdown()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.include_router(api_router)
settings.media_path.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_path), name="media")


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}
