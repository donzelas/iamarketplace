import logging

import httpx

logger = logging.getLogger(__name__)


class TikTokAdsClient:
    """TikTok Marketing API client.

    Docs: https://business-api.tiktok.com/portal/docs
    """

    BASE_URL = "https://business-api.tiktok.com/open_api/v1.3"

    def __init__(self, access_token: str, advertiser_id: str):
        self.token = access_token
        self.advertiser_id = advertiser_id
        self.client = httpx.AsyncClient(
            headers={"Access-Token": access_token},
            timeout=30.0,
        )

    async def get_campaign_report(self, date_from: str, date_to: str) -> list[dict]:
        resp = await self.client.get(
            f"{self.BASE_URL}/report/integrated/get/",
            params={
                "advertiser_id": self.advertiser_id,
                "report_type": "BASIC",
                "data_level": "AUCTION_CAMPAIGN",
                "dimensions": '["campaign_id"]',
                "metrics": '["spend","impressions","clicks","conversion","cost_per_conversion","value_per_conversion"]',
                "start_date": date_from,
                "end_date": date_to,
                "page": 1,
                "page_size": 100,
            },
        )
        resp.raise_for_status()
        data = resp.json().get("data", {}).get("list", [])

        results = []
        for item in data:
            metrics = item.get("metrics", {})
            dims = item.get("dimensions", {})
            spend = float(metrics.get("spend", 0))
            clicks = int(metrics.get("clicks", 0))
            impressions = int(metrics.get("impressions", 0))
            conversions = int(metrics.get("conversion", 0))

            results.append({
                "platform": "tiktok_ads",
                "campaign_id": dims.get("campaign_id"),
                "impressions": impressions,
                "clicks": clicks,
                "spend": spend,
                "orders": conversions,
                "revenue": round(float(metrics.get("value_per_conversion", 0)) * conversions, 2),
                "cpc": round(spend / max(clicks, 1), 2),
                "ctr": round(clicks / max(impressions, 1) * 100, 2),
            })
        return results

    async def update_campaign_budget(self, campaign_id: str, budget: float) -> dict:
        resp = await self.client.post(
            f"{self.BASE_URL}/campaign/update/",
            json={
                "advertiser_id": self.advertiser_id,
                "campaign_id": campaign_id,
                "budget": budget,
            },
        )
        resp.raise_for_status()
        logger.info("TikTok campaign budget updated: %s -> R$%.2f", campaign_id, budget)
        return resp.json()

    async def update_adgroup_bid(self, adgroup_id: str, bid: float) -> dict:
        resp = await self.client.post(
            f"{self.BASE_URL}/adgroup/update/",
            json={
                "advertiser_id": self.advertiser_id,
                "adgroup_id": adgroup_id,
                "bid": bid,
            },
        )
        resp.raise_for_status()
        logger.info("TikTok adgroup bid updated: %s -> R$%.2f", adgroup_id, bid)
        return resp.json()

    async def pause_campaign(self, campaign_id: str) -> dict:
        resp = await self.client.post(
            f"{self.BASE_URL}/campaign/update/status/",
            json={
                "advertiser_id": self.advertiser_id,
                "campaign_ids": [campaign_id],
                "opt_status": "DISABLE",
            },
        )
        resp.raise_for_status()
        logger.info("TikTok campaign paused: %s", campaign_id)
        return resp.json()

    async def close(self):
        await self.client.aclose()
