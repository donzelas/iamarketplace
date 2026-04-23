import logging
import sys

import sentry_sdk
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .api import (
    products_router,
    competitors_router,
    ads_router,
    decisions_router,
    dashboard_router,
)
from .api.auth import router as auth_router

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter(
    "%(asctime)s | %(levelname)-8s | %(name)-30s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
))
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(handler)

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        environment="production",
    )
    logger.info("Sentry initialized")

app = FastAPI(
    title="IA E-commerce - Análise Competitiva",
    description="Sistema de IA para monitoramento de concorrentes, controle de margem e gestão automatizada de ads em múltiplos marketplaces.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(products_router)
app.include_router(competitors_router)
app.include_router(ads_router)
app.include_router(decisions_router)
app.include_router(dashboard_router)


@app.on_event("startup")
async def startup():
    from .database import engine, Base
    from . import models  # noqa: F401
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created / verified")


@app.middleware("http")
async def log_requests(request: Request, call_next):
    logger.info("%s %s", request.method, request.url.path)
    response = await call_next(request)
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Erro interno do servidor"})


@app.get("/")
async def root():
    return {
        "name": "IA E-commerce - Análise Competitiva",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/api/seed")
async def seed_database():
    """Popula o banco com dados fake para desenvolvimento/teste."""
    from .seed import run_seed
    from .database import async_session

    async with async_session() as session:
        try:
            counts = await run_seed(session)
            await session.commit()
            return {"status": "success", "message": "Dados de teste inseridos!", "counts": counts}
        except Exception as e:
            await session.rollback()
            logger.error("Seed failed: %s", e, exc_info=True)
            return JSONResponse(status_code=500, content={"detail": f"Erro no seed: {str(e)}"})
