import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from ..collectors.base import BaseCollector
from ..models import AIDecision, ProductListing

logger = logging.getLogger(__name__)


class ActionExecutor:
    """Executa decisões da IA nos marketplaces e plataformas de ads."""

    def __init__(
        self,
        collectors: dict[str, BaseCollector],
        ads_clients: dict,
        db: AsyncSession,
        auto_execute: bool = False,
    ):
        self.collectors = collectors
        self.ads = ads_clients
        self.db = db
        self.auto_execute = auto_execute

    async def process_decision(self, decision: dict, product, listing) -> dict:
        """Processa uma decisão: salva no banco e executa se permitido."""

        record = AIDecision(
            product_id=product.id,
            decision_type=decision.get("source", "ai"),
            action=decision["action"],
            old_value=float(product.current_price),
            new_value=decision.get("new_price") or decision.get("new_bid") or decision.get("new_budget"),
            reason=decision.get("reason", ""),
            confidence=decision.get("confidence", 0),
            context=decision,
            status="pending",
        )
        self.db.add(record)
        await self.db.flush()

        is_critical = decision.get("urgency") == "critical"
        should_execute = self.auto_execute or is_critical

        if should_execute:
            try:
                result = await self._execute(decision, product, listing)
                record.status = "executed"
                record.executed_at = datetime.utcnow()
                record.result = result
                await self.db.commit()
                logger.info("Decision executed: %s for product %s", decision["action"], product.sku)
                return {"status": "executed", "decision_id": str(record.id), "result": result}
            except Exception as e:
                record.status = "error"
                record.result = {"error": str(e)}
                await self.db.commit()
                logger.error("Decision execution failed: %s", e)
                return {"status": "error", "decision_id": str(record.id), "error": str(e)}

        await self.db.commit()
        logger.info("Decision saved (pending approval): %s for %s", decision["action"], product.sku)
        return {"status": "pending_approval", "decision_id": str(record.id)}

    async def execute_approved(self, decision_record: AIDecision) -> dict:
        """Executa uma decisão que foi aprovada manualmente."""
        product = await self.db.get(type(decision_record.product), decision_record.product_id)
        listings = [l for l in product.listings if l.status == "active"]

        if not listings:
            return {"status": "error", "message": "No active listings found"}

        listing = listings[0]
        decision = decision_record.context or {"action": decision_record.action}

        try:
            result = await self._execute(decision, product, listing)
            decision_record.status = "executed"
            decision_record.executed_at = datetime.utcnow()
            decision_record.result = result
            await self.db.commit()
            return {"status": "executed", "result": result}
        except Exception as e:
            decision_record.status = "error"
            decision_record.result = {"error": str(e)}
            await self.db.commit()
            return {"status": "error", "error": str(e)}

    async def _execute(self, decision: dict, product, listing) -> dict:
        action = decision["action"]
        marketplace = listing.marketplace
        collector = self.collectors.get(marketplace)

        if action in ("ADJUST_PRICE", "RAISE_PRICE"):
            new_price = decision.get("new_price")
            if not new_price:
                return {"type": "error", "message": "No new_price specified"}

            result = {}
            if collector:
                result = await collector.update_price(listing.listing_id, new_price)

            listing.current_price = new_price
            product.current_price = new_price
            return {"type": "price_update", "new_price": new_price, "marketplace_result": result}

        elif action == "REDUCE_BID":
            return await self._update_bid(decision, product, marketplace)

        elif action == "INCREASE_BID":
            return await self._update_bid(decision, product, marketplace)

        elif action == "PAUSE_AD":
            return await self._pause_ad(product, marketplace)

        elif action in ("INCREASE_BUDGET", "REDUCE_BUDGET"):
            return await self._update_budget(decision, product, marketplace)

        elif action == "HOLD":
            return {"type": "no_action", "reason": decision.get("reason", "")}

        return {"type": "unknown_action", "action": action}

    async def _update_bid(self, decision: dict, product, marketplace: str) -> dict:
        ads_client = self.ads.get(marketplace)
        if not ads_client:
            return {"type": "error", "message": f"No ads client for {marketplace}"}

        new_bid = decision.get("new_bid", 0)
        if hasattr(ads_client, "update_campaign_bid"):
            result = await ads_client.update_campaign_bid(str(product.id), new_bid)
        elif hasattr(ads_client, "update_keyword_bid"):
            result = ads_client.update_keyword_bid(str(product.id), "", new_bid)
        else:
            result = {"status": "not_supported"}

        return {"type": "bid_update", "new_bid": new_bid, "result": result}

    async def _pause_ad(self, product, marketplace: str) -> dict:
        ads_client = self.ads.get(marketplace)
        if not ads_client:
            return {"type": "error", "message": f"No ads client for {marketplace}"}

        if hasattr(ads_client, "pause_campaign"):
            result = await ads_client.pause_campaign(str(product.id))
        else:
            result = {"status": "not_supported"}

        return {"type": "ad_paused", "result": result}

    async def _update_budget(self, decision: dict, product, marketplace: str) -> dict:
        ads_client = self.ads.get(marketplace)
        if not ads_client:
            return {"type": "error", "message": f"No ads client for {marketplace}"}

        new_budget = decision.get("new_budget", 0)
        if hasattr(ads_client, "update_campaign_budget"):
            result = await ads_client.update_campaign_budget(str(product.id), new_budget)
        else:
            result = {"status": "not_supported"}

        return {"type": "budget_update", "new_budget": new_budget, "result": result}
