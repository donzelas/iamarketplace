import logging

import httpx

from .base import BaseCollector

logger = logging.getLogger(__name__)


class MercadoLivreCollector(BaseCollector):
    marketplace = "mercadolivre"
    BASE_URL = "https://api.mercadolibre.com"

    def __init__(self, access_token: str, client_id: str = "", client_secret: str = ""):
        self.access_token = access_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30.0,
        )

    async def search_competitors(self, keyword: str, limit: int = 50) -> list[dict]:
        try:
            resp = await self.client.get("/sites/MLB/search", params={
                "q": keyword, "limit": limit, "sort": "relevance",
            })
            resp.raise_for_status()
            results = resp.json().get("results", [])
            return [
                self.normalize_result({
                    "listing_id": r["id"],
                    "title": r["title"],
                    "price": r["price"],
                    "original_price": r.get("original_price"),
                    "seller": r["seller"].get("nickname", ""),
                    "free_shipping": r["shipping"]["free_shipping"],
                    "condition": r["condition"],
                    "sold_quantity": r.get("sold_quantity", 0),
                    "url": r["permalink"],
                    "position": idx + 1,
                })
                for idx, r in enumerate(results)
            ]
        except httpx.HTTPError as e:
            logger.error("ML search error for '%s': %s", keyword, e)
            return []

    async def get_product_details(self, item_id: str) -> dict:
        resp = await self.client.get(f"/items/{item_id}")
        resp.raise_for_status()
        return resp.json()

    async def update_price(self, item_id: str, new_price: float) -> dict:
        resp = await self.client.put(f"/items/{item_id}", json={"price": new_price})
        resp.raise_for_status()
        logger.info("ML price updated: %s -> R$%.2f", item_id, new_price)
        return resp.json()

    async def get_orders(self, seller_id: str, date_from: str) -> list:
        resp = await self.client.get("/orders/search", params={
            "seller": seller_id,
            "order.date_created.from": date_from,
            "sort": "date_desc",
        })
        resp.raise_for_status()
        return resp.json().get("results", [])

    async def get_category_trends(self, category_id: str) -> list:
        resp = await self.client.get(f"/trends/MLB/{category_id}")
        resp.raise_for_status()
        return resp.json()

    async def refresh_token(self, refresh_token: str) -> dict:
        """Renova o access_token usando o refresh_token."""
        resp = await self.client.post("/oauth/token", json={
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
        })
        resp.raise_for_status()
        data = resp.json()
        self.access_token = data["access_token"]
        self.client.headers["Authorization"] = f"Bearer {data['access_token']}"
        logger.info("ML token refreshed successfully")
        return data
