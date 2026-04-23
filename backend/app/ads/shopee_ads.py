import hashlib
import hmac
import logging
import time

import httpx

logger = logging.getLogger(__name__)


class ShopeeAdsClient:
    """Shopee Ads API client.

    Usa a mesma autenticação do Shopee Open Platform.
    """

    BASE_URL = "https://partner.shopeemobile.com/api/v2"

    def __init__(self, partner_id: int, partner_key: str, shop_id: int, access_token: str):
        self.partner_id = partner_id
        self.partner_key = partner_key
        self.shop_id = shop_id
        self.access_token = access_token
        self.client = httpx.AsyncClient(timeout=30.0)

    def _sign(self, path: str, timestamp: int) -> str:
        base_string = f"{self.partner_id}{path}{timestamp}{self.access_token}{self.shop_id}"
        return hmac.new(
            self.partner_key.encode(), base_string.encode(), hashlib.sha256
        ).hexdigest()

    def _common_params(self, path: str) -> dict:
        ts = int(time.time())
        return {
            "partner_id": self.partner_id,
            "timestamp": ts,
            "sign": self._sign(path, ts),
            "access_token": self.access_token,
            "shop_id": self.shop_id,
        }

    async def get_campaign_performance(self, date_from: str, date_to: str) -> list[dict]:
        path = "/ads/get_all_ads_daily_performance"
        params = self._common_params(path)
        params.update({"start_date": date_from, "end_date": date_to})

        resp = await self.client.get(f"{self.BASE_URL}{path}", params=params)
        resp.raise_for_status()
        data = resp.json().get("response", {}).get("daily_performance", [])

        results = []
        for item in data:
            impressions = item.get("impression", 0)
            clicks = item.get("click", 0)
            spend = float(item.get("expense", 0))
            orders = item.get("order", 0)
            revenue = float(item.get("broad_order_amount", 0))

            results.append({
                "platform": "shopee_ads",
                "date": item.get("date"),
                "impressions": impressions,
                "clicks": clicks,
                "spend": spend,
                "orders": orders,
                "revenue": revenue,
                "cpc": round(spend / max(clicks, 1), 2),
                "ctr": round(clicks / max(impressions, 1) * 100, 2),
                "roas": round(revenue / max(spend, 0.01), 2),
            })
        return results

    async def update_campaign_bid(self, campaign_id: str, new_bid: float) -> dict:
        path = "/ads/update_cpc_bid"
        params = self._common_params(path)
        resp = await self.client.post(
            f"{self.BASE_URL}{path}",
            params=params,
            json={"campaign_id": int(campaign_id), "cpc_bid": new_bid},
        )
        resp.raise_for_status()
        logger.info("Shopee Ads bid updated: %s -> R$%.2f", campaign_id, new_bid)
        return resp.json()

    async def pause_campaign(self, campaign_id: str) -> dict:
        path = "/ads/update_ads_status"
        params = self._common_params(path)
        resp = await self.client.post(
            f"{self.BASE_URL}{path}",
            params=params,
            json={"campaign_id": int(campaign_id), "status": "paused"},
        )
        resp.raise_for_status()
        logger.info("Shopee Ads campaign paused: %s", campaign_id)
        return resp.json()

    async def close(self):
        await self.client.aclose()
