import logging

import httpx

logger = logging.getLogger(__name__)


class MetaAdsClient:
    """Meta Marketing API client (Facebook/Instagram Ads).

    Docs: https://developers.facebook.com/docs/marketing-apis
    """

    BASE_URL = "https://graph.facebook.com/v19.0"

    def __init__(self, access_token: str, ad_account_id: str):
        self.token = access_token
        self.account_id = ad_account_id
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_campaign_performance(self, date_from: str, date_to: str) -> list[dict]:
        resp = await self.client.get(
            f"{self.BASE_URL}/act_{self.account_id}/insights",
            params={
                "access_token": self.token,
                "level": "campaign",
                "fields": ",".join([
                    "campaign_name", "campaign_id", "impressions", "clicks",
                    "spend", "actions", "cost_per_action_type", "purchase_roas",
                ]),
                "time_range": f'{{"since":"{date_from}","until":"{date_to}"}}',
            },
        )
        resp.raise_for_status()
        data = resp.json().get("data", [])

        results = []
        for item in data:
            purchases = self._extract_action(item.get("actions", []), "purchase")
            revenue = self._extract_action_value(item.get("action_values", []), "purchase")
            spend = float(item.get("spend", 0))

            results.append({
                "platform": "meta_ads",
                "campaign_id": item.get("campaign_id"),
                "campaign_name": item.get("campaign_name"),
                "impressions": int(item.get("impressions", 0)),
                "clicks": int(item.get("clicks", 0)),
                "spend": spend,
                "orders": purchases,
                "revenue": revenue,
                "cpc": round(spend / max(int(item.get("clicks", 0)), 1), 2),
                "roas": round(revenue / max(spend, 0.01), 2),
            })
        return results

    async def update_campaign_budget(self, campaign_id: str, daily_budget_cents: int) -> dict:
        resp = await self.client.post(
            f"{self.BASE_URL}/{campaign_id}",
            params={"access_token": self.token, "daily_budget": daily_budget_cents},
        )
        resp.raise_for_status()
        logger.info("Meta campaign budget updated: %s -> %d cents", campaign_id, daily_budget_cents)
        return resp.json()

    async def update_adset_bid(self, adset_id: str, bid_amount_cents: int) -> dict:
        resp = await self.client.post(
            f"{self.BASE_URL}/{adset_id}",
            params={"access_token": self.token, "bid_amount": bid_amount_cents},
        )
        resp.raise_for_status()
        logger.info("Meta adset bid updated: %s -> %d cents", adset_id, bid_amount_cents)
        return resp.json()

    async def pause_campaign(self, campaign_id: str) -> dict:
        resp = await self.client.post(
            f"{self.BASE_URL}/{campaign_id}",
            params={"access_token": self.token, "status": "PAUSED"},
        )
        resp.raise_for_status()
        logger.info("Meta campaign paused: %s", campaign_id)
        return resp.json()

    async def search_ad_library(self, keyword: str, limit: int = 50) -> list[dict]:
        """Busca anúncios de concorrentes na Ad Library (pública)."""
        resp = await self.client.get(
            f"{self.BASE_URL}/ads_archive",
            params={
                "access_token": self.token,
                "search_terms": keyword,
                "ad_reached_countries": '["BR"]',
                "ad_type": "ALL",
                "fields": "ad_creative_bodies,ad_creative_link_titles,page_name,spend,impressions",
                "limit": limit,
            },
        )
        resp.raise_for_status()
        return resp.json().get("data", [])

    async def close(self):
        await self.client.aclose()

    @staticmethod
    def _extract_action(actions: list, action_type: str) -> int:
        for a in actions:
            if a.get("action_type") == action_type:
                return int(a.get("value", 0))
        return 0

    @staticmethod
    def _extract_action_value(action_values: list, action_type: str) -> float:
        for a in action_values:
            if a.get("action_type") == action_type:
                return float(a.get("value", 0))
        return 0.0
