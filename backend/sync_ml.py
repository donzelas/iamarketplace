"""
Sincroniza métricas reais dos anúncios do Mercado Livre:
- Preço atual, sold_quantity, available_quantity
- Visitas (30 dias)
- Revenue estimado (sold_quantity * price)
- Conversion rate (sold/visits)

Uso:
    python sync_ml.py
"""
import asyncio
import logging
import sys
from datetime import datetime

import httpx
from sqlalchemy import select

from app.database import engine, async_session, Base
from app.models import ProductListing, Product, SystemConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("sync_ml")

ML_API = "https://api.mercadolibre.com"


async def get_access_token(db) -> str:
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == "ml_access_token"))
    config = result.scalar_one_or_none()
    if config:
        return config.value["token"]
    raise RuntimeError("Token ML não encontrado. Autorize via /api/auth/mercadolivre/authorize")


async def fetch_visits_batch(client: httpx.AsyncClient, item_ids: list[str]) -> dict[str, int]:
    """Busca visitas dos últimos 30 dias para cada item."""
    visits = {}
    for item_id in item_ids:
        try:
            resp = await client.get(
                f"{ML_API}/items/{item_id}/visits/time_window",
                params={"last": 30, "unit": "day"},
            )
            if resp.status_code == 200:
                data = resp.json()
                total = sum(r.get("total", 0) for r in data.get("results", []))
                visits[item_id] = total
            else:
                visits[item_id] = 0
        except Exception:
            visits[item_id] = 0
    return visits


async def main():
    logger.info("=== SINCRONIZAÇÃO DE MÉTRICAS ML ===")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        token = await get_access_token(db)
        logger.info("Token: %s...", token[:20])

        result = await db.execute(
            select(ProductListing).where(ProductListing.marketplace == "mercadolivre")
        )
        listings = result.scalars().all()
        logger.info("Listings ML encontrados: %d", len(listings))

        listing_map = {l.listing_id: l for l in listings}
        all_ids = list(listing_map.keys())

        updated = 0
        async with httpx.AsyncClient(
            headers={"Authorization": f"Bearer {token}"},
            timeout=15.0,
        ) as client:

            # 1) Atualizar dados do item (preço, sold, available, thumbnail, etc)
            for i in range(0, len(all_ids), 20):
                batch_ids = all_ids[i:i + 20]
                ids_str = ",".join(batch_ids)
                resp = await client.get(f"{ML_API}/items", params={"ids": ids_str})
                if resp.status_code != 200:
                    logger.warning("Items batch falhou: %s", resp.status_code)
                    continue

                for wrapper in resp.json():
                    if wrapper.get("code") != 200:
                        continue
                    item = wrapper["body"]
                    lid = item["id"]
                    listing = listing_map.get(lid)
                    if not listing:
                        continue

                    listing.current_price = float(item.get("price", listing.current_price))
                    listing.original_price = float(item.get("original_price") or 0) or None
                    listing.sold_quantity = item.get("sold_quantity", 0)
                    listing.available_quantity = item.get("available_quantity", 0)
                    listing.free_shipping = item.get("shipping", {}).get("free_shipping", False)
                    listing.status = "active" if item.get("status") == "active" else "paused"
                    listing.thumbnail = item.get("thumbnail", listing.thumbnail)
                    listing.condition = item.get("condition", listing.condition)
                    listing.listing_type = item.get("listing_type_id", listing.listing_type)
                    listing.health = item.get("health", listing.health)

                    fee_pct = 16.0 if "gold" in (listing.listing_type or "") else 11.0
                    listing.marketplace_fee_pct = fee_pct

                    listing.revenue_total = round(listing.sold_quantity * listing.current_price, 2)

                    product = await db.get(Product, listing.product_id)
                    if product:
                        product.current_price = listing.current_price
                        product.status = listing.status

                    updated += 1

                logger.info("Items atualizados: %d/%d", min(i + 20, len(all_ids)), len(all_ids))

            # 2) Buscar visitas (em blocos menores para não estourar rate limit)
            logger.info("Buscando visitas...")
            visits_updated = 0
            for i in range(0, len(all_ids), 10):
                batch_ids = all_ids[i:i + 10]
                visits = await fetch_visits_batch(client, batch_ids)
                for lid, v in visits.items():
                    listing = listing_map.get(lid)
                    if listing:
                        listing.visits_total = v
                        if listing.sold_quantity > 0 and v > 0:
                            listing.conversion_rate = round((listing.sold_quantity / v) * 100, 2)
                        else:
                            listing.conversion_rate = 0
                        listing.synced_at = datetime.utcnow()
                        visits_updated += 1

                logger.info("Visitas: %d/%d", min(i + 10, len(all_ids)), len(all_ids))
                await asyncio.sleep(0.3)

        await db.commit()

    logger.info("=== SINCRONIZAÇÃO COMPLETA ===")
    logger.info("Listings atualizados: %d", updated)
    logger.info("Visitas atualizados: %d", visits_updated)


if __name__ == "__main__":
    asyncio.run(main())
