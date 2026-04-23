import asyncio
import logging

from .celery_app import celery_app

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper para rodar coroutines dentro de tasks Celery síncronas."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.tasks.monitoring_tasks.collect_competitor_data", bind=True, max_retries=3)
def collect_competitor_data(self):
    """Coleta preços de concorrentes em todos os marketplaces."""
    try:
        run_async(_collect_competitor_data())
    except Exception as exc:
        logger.error("Competitor data collection failed: %s", exc)
        self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task(name="app.tasks.monitoring_tasks.analyze_and_decide", bind=True, max_retries=3)
def analyze_and_decide(self):
    """Analisa mercado e gera decisões para cada produto."""
    try:
        run_async(_analyze_and_decide())
    except Exception as exc:
        logger.error("Analysis and decision failed: %s", exc)
        self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task(name="app.tasks.monitoring_tasks.collect_ads_performance", bind=True, max_retries=3)
def collect_ads_performance(self):
    """Coleta métricas de ads de todas as plataformas."""
    try:
        run_async(_collect_ads_performance())
    except Exception as exc:
        logger.error("Ads performance collection failed: %s", exc)
        self.retry(exc=exc, countdown=60 * (self.request.retries + 1))


@celery_app.task(name="app.tasks.monitoring_tasks.daily_margin_snapshots")
def daily_margin_snapshots():
    """Gera snapshot diário de margem para todos os produtos."""
    try:
        run_async(_daily_margin_snapshots())
    except Exception as exc:
        logger.error("Daily margin snapshots failed: %s", exc)


async def _collect_competitor_data():
    from ..database import async_session
    from ..config import settings
    from ..collectors import MercadoLivreCollector, MarketplaceScraper, UnifiedDataCollector
    from ..models import Product, Competitor, CompetitorPriceHistory
    from sqlalchemy import select
    from datetime import datetime

    async with async_session() as db:
        result = await db.execute(select(Product).where(Product.status == "active"))
        products = result.scalars().all()

        collectors = {}
        if settings.ml_access_token:
            collectors["mercadolivre"] = MercadoLivreCollector(settings.ml_access_token)

        orchestrator = UnifiedDataCollector(collectors, MarketplaceScraper())

        for product in products:
            keywords = (product.keywords or product.name).split(",")
            for keyword in keywords[:3]:
                keyword = keyword.strip()
                if not keyword:
                    continue

                competitors = await orchestrator.collect_competitor_data(keyword, limit=20)

                for comp_data in competitors:
                    comp = Competitor(
                        product_id=product.id,
                        marketplace=comp_data["marketplace"],
                        competitor_listing_id=comp_data.get("listing_id"),
                        competitor_seller=comp_data.get("seller"),
                        competitor_name=comp_data.get("title"),
                        last_price=comp_data["price"],
                        last_seen_at=datetime.utcnow(),
                    )
                    db.add(comp)
                    await db.flush()

                    price_record = CompetitorPriceHistory(
                        competitor_id=comp.id,
                        product_id=product.id,
                        marketplace=comp_data["marketplace"],
                        price=comp_data["price"],
                        original_price=comp_data.get("original_price"),
                        free_shipping=comp_data.get("free_shipping", False),
                        seller_name=comp_data.get("seller"),
                        position_in_search=comp_data.get("position"),
                    )
                    db.add(price_record)

                logger.info("Collected %d competitors for '%s' (%s)", len(competitors), keyword, product.sku)

        await db.commit()
        for c in collectors.values():
            await c.close()


async def _analyze_and_decide():
    from ..database import async_session
    from ..config import settings
    from ..analysis import MarketAnalyzer, MarginCalculator
    from ..engine import DecisionEngine, RulesEngine
    from ..executor import ActionExecutor
    from ..models import Product, ProductListing
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from openai import AsyncOpenAI

    async with async_session() as db:
        result = await db.execute(
            select(Product)
            .where(Product.status == "active")
            .options(selectinload(Product.listings))
        )
        products = result.scalars().all()

        analyzer = MarketAnalyzer(db)
        margin_calc = MarginCalculator()

        config = {"llm_model": settings.llm_model, "max_acos": 30, "global_min_margin_pct": 10, "max_price_change_pct": 10}
        rules = RulesEngine(config)

        llm_client = AsyncOpenAI(api_key=settings.openai_api_key)
        engine = DecisionEngine(llm_client, rules, config)
        executor = ActionExecutor({}, {}, db, settings.auto_execute)

        for product in products:
            active_listings = [l for l in product.listings if l.status == "active"]
            if not active_listings:
                continue

            for listing in active_listings:
                market_analysis = await analyzer.analyze_product(str(product.id))
                if market_analysis.get("status") in ("not_found", "no_data"):
                    continue

                margin_data = margin_calc.calculate(product, listing)
                decision = await engine.evaluate(product, market_analysis, margin_data)

                if decision["action"] != "HOLD":
                    await executor.process_decision(decision, product, listing)

        await db.commit()
        await llm_client.close()


async def _collect_ads_performance():
    logger.info("Collecting ads performance from all platforms...")
    # Implementar coleta de cada plataforma de ads configurada


async def _daily_margin_snapshots():
    from ..database import async_session
    from ..margin import MarginController
    from ..models import Product
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    async with async_session() as db:
        config = {"global_min_margin_pct": 10, "global_target_margin_pct": 25, "global_alert_margin_pct": 15}
        controller = MarginController(config, db)

        result = await db.execute(
            select(Product)
            .where(Product.status == "active")
            .options(selectinload(Product.listings))
        )
        products = result.scalars().all()

        for product in products:
            for listing in product.listings:
                if listing.status == "active":
                    await controller.create_snapshot(product, listing)

        await db.commit()
        logger.info("Daily margin snapshots created for %d products", len(products))
