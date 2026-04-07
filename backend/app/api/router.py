from fastapi import APIRouter

from app.api.routes import accounts, debug, jobs, models, schedules, search

api_router = APIRouter(prefix="/api")
api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(models.router, prefix="/models", tags=["models"])
api_router.include_router(schedules.router, prefix="/schedules", tags=["schedules"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(debug.router, prefix="/debug", tags=["debug"])
