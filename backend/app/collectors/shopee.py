import hashlib
import hmac
import logging
import time

import httpx

from .base import BaseCollector

logger = logging.getLogger(__name__)


class ShopeeCollector(BaseCollector):
    marketplace = "shopee"
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

    async def search_competitors(self, keyword: str, limit: int = 50) -> list[dict]:
        """Shopee não tem API pública de busca — usa scraper para concorrentes."""
        logger.info("Shopee search requires scraper for keyword: %s", keyword)
        return []

    async def get_product_details(self, item_id: str) -> dict:
        path = "/product/get_item_base_info"
        params = self._common_params(path)
        params["item_id_list"] = item_id
        resp = await self.client.get(f"{self.BASE_URL}{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_my_items(self, offset: int = 0, limit: int = 50) -> dict:
        path = "/product/get_item_list"
        params = self._common_params(path)
        params.update({"offset": offset, "page_size": limit, "item_status": "NORMAL"})
        resp = await self.client.get(f"{self.BASE_URL}{path}", params=params)
        resp.raise_for_status()
        return resp.json()

    async def update_price(self, item_id: str, new_price: float) -> dict:
        path = "/product/update_price"
        params = self._common_params(path)
        resp = await self.client.post(
            f"{self.BASE_URL}{path}",
            params=params,
            json={"item_list": [{"item_id": int(item_id), "price_list": [{"original_price": new_price}]}]},
        )
        resp.raise_for_status()
        logger.info("Shopee price updated: %s -> R$%.2f", item_id, new_price)
        return resp.json()

    async def get_shop_performance(self) -> dict:
        path = "/shop/performance"
        params = self._common_params(path)
        resp = await self.client.get(f"{self.BASE_URL}{path}", params=params)
        resp.raise_for_status()
        return resp.json()
