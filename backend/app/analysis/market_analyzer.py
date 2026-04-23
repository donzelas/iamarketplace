import logging
from datetime import datetime, timedelta
from statistics import mean, median, stdev

from sqlalchemy import select, func as sqla_func
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import CompetitorPriceHistory, Product

logger = logging.getLogger(__name__)


class MarketAnalyzer:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def analyze_product(self, product_id: str) -> dict:
        product = await self.db.get(Product, product_id)
        if not product:
            return {"status": "not_found", "product_id": product_id}

        recent_prices = await self._get_recent_prices(product_id, hours=24)
        if not recent_prices:
            return {"status": "no_data", "product_id": product_id}

        prices = [float(p.price) for p in recent_prices]
        my_price = float(product.current_price)

        analysis = {
            "product_id": str(product_id),
            "product_name": product.name,
            "my_price": my_price,
            "competitor_count": len(set(str(p.competitor_id) for p in recent_prices)),
            "price_stats": {
                "min": min(prices),
                "max": max(prices),
                "avg": round(mean(prices), 2),
                "median": round(median(prices), 2),
                "stdev": round(stdev(prices), 2) if len(prices) > 1 else 0,
            },
            "my_position": self._calc_position(my_price, prices),
            "price_gap": {
                "vs_min": round(my_price - min(prices), 2),
                "vs_min_pct": round((my_price - min(prices)) / max(min(prices), 0.01) * 100, 2),
                "vs_avg": round(my_price - mean(prices), 2),
                "vs_avg_pct": round((my_price - mean(prices)) / max(mean(prices), 0.01) * 100, 2),
            },
            "free_shipping_competitors": sum(1 for p in recent_prices if p.free_shipping),
            "trend": await self._calc_trend(product_id),
            "marketplaces": self._group_by_marketplace(recent_prices),
            "analyzed_at": datetime.utcnow().isoformat(),
        }

        logger.info("Analysis complete for product %s: position #%d/%d", product.name, analysis["my_position"]["rank"], analysis["my_position"]["total"])
        return analysis

    async def _get_recent_prices(self, product_id: str, hours: int = 24) -> list:
        since = datetime.utcnow() - timedelta(hours=hours)
        result = await self.db.execute(
            select(CompetitorPriceHistory)
            .where(CompetitorPriceHistory.product_id == product_id)
            .where(CompetitorPriceHistory.collected_at >= since)
            .order_by(CompetitorPriceHistory.collected_at.desc())
        )
        return result.scalars().all()

    async def _get_avg_price(self, product_id: str, hours: int) -> float | None:
        since = datetime.utcnow() - timedelta(hours=hours)
        result = await self.db.execute(
            select(sqla_func.avg(CompetitorPriceHistory.price))
            .where(CompetitorPriceHistory.product_id == product_id)
            .where(CompetitorPriceHistory.collected_at >= since)
        )
        val = result.scalar_one_or_none()
        return float(val) if val else None

    async def _calc_trend(self, product_id: str) -> dict:
        avg_24h = await self._get_avg_price(product_id, 24)
        avg_72h = await self._get_avg_price(product_id, 72)
        avg_7d = await self._get_avg_price(product_id, 168)

        if not all([avg_24h, avg_72h]):
            return {"direction": "unknown", "change_pct_72h": 0}

        change = (avg_24h - avg_72h) / max(avg_72h, 0.01) * 100

        if change > 2:
            direction = "rising"
        elif change < -2:
            direction = "falling"
        else:
            direction = "stable"

        return {
            "direction": direction,
            "avg_24h": round(avg_24h, 2) if avg_24h else None,
            "avg_72h": round(avg_72h, 2) if avg_72h else None,
            "avg_7d": round(avg_7d, 2) if avg_7d else None,
            "change_pct_72h": round(change, 2),
        }

    @staticmethod
    def _calc_position(my_price: float, competitor_prices: list[float]) -> dict:
        all_prices = sorted(set(competitor_prices + [my_price]))
        rank = all_prices.index(my_price) + 1
        total = len(all_prices)
        return {
            "rank": rank,
            "total": total,
            "percentile": round((1 - rank / max(total, 1)) * 100, 1),
        }

    @staticmethod
    def _group_by_marketplace(prices) -> dict:
        grouped: dict[str, list[float]] = {}
        for p in prices:
            mp = p.marketplace
            grouped.setdefault(mp, []).append(float(p.price))

        return {
            mp: {
                "count": len(plist),
                "min": min(plist),
                "avg": round(mean(plist), 2),
                "max": max(plist),
            }
            for mp, plist in grouped.items()
        }
