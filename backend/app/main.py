import logging

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .api import (
    products_router,
    competitors_router,
    ads_router,
    decisions_router,
    dashboard_router,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)

if settings.sentry_dsn:
    sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1)

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

app.include_router(products_router)
app.include_router(competitors_router)
app.include_router(ads_router)
app.include_router(decisions_router)
app.include_router(dashboard_router)


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
