"""AgentCare FastAPI application entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import AppError, app_error_handler
from app.api.routes import auth, departments, patients, staff, workflows
from app.core.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
)
logger = logging.getLogger("agentcare")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure storage dir exists.
    settings.storage_path.mkdir(parents=True, exist_ok=True)

    if settings.auto_init_db:
        from app.db.init_db import create_all

        create_all()
        logger.info("Database tables ensured (auto_init_db).")

    if settings.auto_seed:
        from sqlalchemy import func, select

        from app.core.db import session_scope
        from app.models import Department
        from app.db.seed import seed_all

        with session_scope() as db:
            has_data = db.scalar(select(func.count(Department.id))) or 0
        if not has_data:
            counts = seed_all(create_tables=False)
            logger.info("Seeded synthetic data: %s", counts)

        if settings.seed_demo_workflows:
            try:
                from app.db.seed_workflows import seed_demo_workflows

                n = seed_demo_workflows()
                if n:
                    logger.info("Seeded %d demo workflow runs.", n)
            except Exception as exc:  # never let demo seeding break startup
                logger.warning("Demo workflow seeding skipped: %s", exc)
    yield


app = FastAPI(
    title="AgentCare API",
    description="Agentic AI for patient administration and care coordination.",
    version="1.0.0",
    lifespan=lifespan,
)

# Auth uses Bearer tokens (not cookies), so a wildcard origin is safe when configured.
_origins = settings.cors_origins
_allow_all = "*" in _origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _allow_all else _origins,
    allow_credentials=not _allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(AppError, app_error_handler)

app.include_router(auth.router, prefix=settings.api_v1_prefix)
app.include_router(departments.router, prefix=settings.api_v1_prefix)
app.include_router(patients.router, prefix=settings.api_v1_prefix)
app.include_router(workflows.router, prefix=settings.api_v1_prefix)
app.include_router(staff.router, prefix=settings.api_v1_prefix)


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "llm_provider": settings.llm_provider if settings.use_real_llm else "mock",
    }
