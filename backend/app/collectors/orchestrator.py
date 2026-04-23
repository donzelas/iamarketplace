import asyncio
import logging
from datetime import datetime

from .base import BaseCollector
from .scraper import MarketplaceScraper

logger = logging.getLogger(__name__)


class UnifiedDataCollector:
    """Orquestra coleta de dados de todos os marketplaces e scrapers."""

    def __init__(
        self,
        collectors: dict[str, BaseCollector],
        scraper: MarketplaceScraper | None = None,
    ):
        self.collectors = collectors
        self.scraper = scraper or MarketplaceScraper()

    async def collect_competitor_data(self, keyword: str, limit: int = 30) -> list[dict]:
        """Coleta dados de concorrentes de TODOS os marketplaces em paralelo."""
        tasks = []

        for name, collector in self.collectors.items():
            tasks.append(self._safe_collect(collector, keyword, limit, name))

        scraper_marketplaces = ["mercadolivre", "shopee", "amazon", "magalu"]
        for mp in scraper_marketplaces:
            tasks.append(self._safe_scrape(mp, keyword, limit))

        results = await asyncio.gather(*tasks)

        all_competitors: list[dict] = []
        for result in results:
            if isinstance(result, list):
                all_competitors.extend(result)

        seen = set()
        deduplicated = []
        for item in all_competitors:
            key = (item.get("marketplace"), item.get("title", "")[:50], item.get("price"))
            if key not in seen:
                seen.add(key)
                deduplicated.append(item)

        logger.info("Collected %d unique competitor listings for '%s'", len(deduplicated), keyword)
        return deduplicated

    async def collect_ads_performance(self, ads_clients: dict, date_from: str, date_to: str) -> dict:
        """Coleta métricas de ads de TODAS as plataformas em paralelo."""
        tasks = {}
        for platform, client in ads_clients.items():
            if hasattr(client, "get_campaign_performance"):
                tasks[platform] = client.get_campaign_performance(date_from, date_to)
            elif hasattr(client, "get_campaign_report"):
                tasks[platform] = client.get_campaign_report(date_from, date_to)

        results = {}
        gathered = await asyncio.gather(*tasks.values(), return_exceptions=True)
        for platform, result in zip(tasks.keys(), gathered):
            if isinstance(result, Exception):
                logger.error("Ads collection error for %s: %s", platform, result)
                results[platform] = {"error": str(result)}
            else:
                results[platform] = result

        total_spend = sum(
            self._extract_spend(v) for v in results.values() if not isinstance(v, dict) or "error" not in v
        )
        results["total_spend"] = total_spend
        return results

    async def _safe_collect(self, collector: BaseCollector, keyword: str, limit: int, name: str) -> list[dict]:
        try:
            return await collector.search_competitors(keyword, limit)
        except Exception as e:
            logger.error("Collector %s error: %s", name, e)
            return []

    async def _safe_scrape(self, marketplace: str, keyword: str, limit: int) -> list[dict]:
        try:
            return await self.scraper.scrape_search_results(marketplace, keyword, limit)
        except Exception as e:
            logger.error("Scraper %s error: %s", marketplace, e)
            return []

    @staticmethod
    def _extract_spend(data) -> float:
        if isinstance(data, list):
            return sum(float(item.get("spend", 0)) for item in data)
        if isinstance(data, dict):
            return float(data.get("spend", 0))
        return 0.0
