import logging

import httpx

logger = logging.getLogger(__name__)


class MercadoAdsClient:
    """Mercado Livre Product Ads API client.

    Usa a mesma autenticação OAuth do Mercado Livre.
    """

    BASE_URL = "https://api.mercadolibre.com/advertising"

    def __init__(self, access_token: str):
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30.0,
        )

    async def get_campaigns(self) -> list[dict]:
        resp = await self.client.get(f"{self.BASE_URL}/product_ads/campaigns")
        resp.raise_for_status()
        return resp.json()

    async def get_campaign_performance(self, date_from: str, date_to: str) -> list[dict]:
        campaigns = await self.get_campaigns()
        results = []
        for campaign in campaigns:
            cid = campaign.get("id") or campaign.get("campaign_id")
            if not cid:
                continue
            try:
                metrics = await self.get_campaign_metrics(str(cid), date_from, date_to)
                results.append({
                    "platform": "mercado_ads",
                    "campaign_id": str(cid),
                    "campaign_name": campaign.get("name", ""),
                    **metrics,
                })
            except Exception as e:
                logger.error("Error fetching ML ads metrics for campaign %s: %s", cid, e)
        return results

    async def get_campaign_metrics(self, campaign_id: str, date_from: str, date_to: str) -> dict:
        resp = await self.client.get(
            f"{self.BASE_URL}/product_ads/campaigns/{campaign_id}/metrics",
            params={"date_from": date_from, "date_to": date_to},
        )
        resp.raise_for_status()
        data = resp.json()

        impressions = data.get("impressions", 0)
        clicks = data.get("clicks", 0)
        spend = float(data.get("cost", 0))
        orders = data.get("orders", 0)
        revenue = float(data.get("revenue", 0))

        return {
            "impressions": impressions,
            "clicks": clicks,
            "spend": spend,
            "orders": orders,
            "revenue": revenue,
            "cpc": round(spend / max(clicks, 1), 2),
            "ctr": round(clicks / max(impressions, 1) * 100, 2),
            "acos": round(spend / max(revenue, 0.01) * 100, 2),
            "roas": round(revenue / max(spend, 0.01), 2),
        }

    async def update_campaign_budget(self, campaign_id: str, daily_budget: float) -> dict:
        resp = await self.client.put(
            f"{self.BASE_URL}/product_ads/campaigns/{campaign_id}",
            json={"daily_budget": daily_budget},
        )
        resp.raise_for_status()
        logger.info("ML Ads budget updated: %s -> R$%.2f", campaign_id, daily_budget)
        return resp.json()

    async def pause_campaign(self, campaign_id: str) -> dict:
        resp = await self.client.put(
            f"{self.BASE_URL}/product_ads/campaigns/{campaign_id}",
            json={"status": "paused"},
        )
        resp.raise_for_status()
        logger.info("ML Ads campaign paused: %s", campaign_id)
        return resp.json()

    async def close(self):
        await self.client.aclose()
