import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ..analysis.margin_calculator import MarginCalculator
from ..models import MarginSnapshot

logger = logging.getLogger(__name__)


class MarginController:
    """Monitora saúde das margens e salva snapshots."""

    def __init__(self, config: dict, db: AsyncSession):
        self.min_margin = float(config.get("global_min_margin_pct", 10))
        self.target_margin = float(config.get("global_target_margin_pct", 25))
        self.alert_margin = float(config.get("global_alert_margin_pct", 15))
        self.calculator = MarginCalculator()
        self.db = db

    def check_health(self, margin_pct: float) -> str:
        if margin_pct >= self.target_margin:
            return "HEALTHY"
        elif margin_pct >= self.alert_margin:
            return "WARNING"
        elif margin_pct >= self.min_margin:
            return "CRITICAL"
        else:
            return "EMERGENCY"

    async def create_snapshot(self, product, listing, ad_data: dict | None = None) -> dict:
        """Calcula margem e salva snapshot no banco."""
        margin_data = self.calculator.calculate(product, listing, ad_data)
        health = self.check_health(margin_data["margin_pct"])

        snapshot = MarginSnapshot(
            product_id=product.id,
            sale_price=margin_data["sale_price"],
            cost=margin_data["cost"],
            marketplace_fee=margin_data["marketplace_fee"],
            shipping_cost=margin_data["shipping_cost"],
            ad_cost_per_sale=margin_data["ad_cost_per_sale"],
            net_profit=margin_data["net_profit"],
            margin_pct=margin_data["margin_pct"],
            health_status=health,
        )
        self.db.add(snapshot)
        await self.db.flush()

        margin_data["health_status"] = health

        if health in ("CRITICAL", "EMERGENCY"):
            logger.warning(
                "Margin alert for %s: %.1f%% (%s)",
                product.sku, margin_data["margin_pct"], health,
            )

        return margin_data

    def max_price_reduction(self, product, listing, ad_data: dict | None = None) -> float:
        """Calcula o máximo que o preço pode cair mantendo margem mínima."""
        min_price = self.calculator.min_price_for_margin(product, listing, self.min_margin, ad_data)
        current_price = float(listing.current_price)
        return round(max(current_price - min_price, 0), 2)
