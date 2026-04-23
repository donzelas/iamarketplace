import logging

import httpx

from .base import BaseCollector

logger = logging.getLogger(__name__)


class MagaluCollector(BaseCollector):
    """Magazine Luiza Marketplace API.

    Documentação: dev.magalu.com
    A API é focada no seller (seus produtos/pedidos).
    Para concorrentes, usa o MarketplaceScraper.
    """

    marketplace = "magalu"
    BASE_URL = "https://api.marketplace.magalu.com"

    def __init__(self, api_key: str, tenant_id: str):
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={"Authorization": f"Bearer {api_key}", "X-Tenant-Id": tenant_id},
            timeout=30.0,
        )

    async def search_competitors(self, keyword: str, limit: int = 50) -> list[dict]:
        """Magalu não tem API de busca pública — usa scraper."""
        logger.info("Magalu search requires scraper for: %s", keyword)
        return []

    async def get_product_details(self, sku: str) -> dict:
        resp = await self.client.get(f"/v1/products/{sku}")
        resp.raise_for_status()
        return resp.json()

    async def get_my_products(self, offset: int = 0, limit: int = 50) -> dict:
        resp = await self.client.get("/v1/products", params={
            "offset": offset, "limit": limit, "status": "active",
        })
        resp.raise_for_status()
        return resp.json()

    async def update_price(self, sku: str, new_price: float) -> dict:
        resp = await self.client.put(f"/v1/products/{sku}/prices", json={
            "price": new_price,
            "promotional_price": new_price,
        })
        resp.raise_for_status()
        logger.info("Magalu price updated: %s -> R$%.2f", sku, new_price)
        return resp.json()

    async def get_orders(self, status: str = "new") -> dict:
        resp = await self.client.get("/v1/orders", params={"status": status})
        resp.raise_for_status()
        return resp.json()

    async def update_stock(self, sku: str, quantity: int) -> dict:
        resp = await self.client.put(f"/v1/products/{sku}/stocks", json={
            "quantity": quantity,
        })
        resp.raise_for_status()
        return resp.json()
