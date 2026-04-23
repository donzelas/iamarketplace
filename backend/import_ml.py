"""
Importa anúncios reais do Mercado Livre para o banco de dados.

Uso:
    python import_ml.py
"""
import asyncio
import logging
import sys
import uuid
from datetime import datetime

import httpx
from sqlalchemy import select

from app.config import settings
from app.database import engine, async_session, Base
from app.models import Product, ProductListing, Competitor, CompetitorPriceHistory, SystemConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("import_ml")

ML_API = "https://api.mercadolibre.com"


def _uid() -> str:
    return str(uuid.uuid4())


async def get_access_token(db) -> str:
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == "ml_access_token"))
    config = result.scalar_one_or_none()
    if config:
        return config.value["token"]
    if settings.ml_access_token:
        return settings.ml_access_token
    raise RuntimeError("Nenhum access_token do ML disponível. Autorize via /api/auth/mercadolivre/authorize")


async def fetch_all_item_ids(client: httpx.AsyncClient, user_id: str) -> list[str]:
    """Busca todos os IDs de anúncios do vendedor."""
    all_ids = []
    offset = 0
    limit = 50
    while True:
        resp = await client.get(f"{ML_API}/users/{user_id}/items/search", params={"limit": limit, "offset": offset})
        resp.raise_for_status()
        data = resp.json()
        all_ids.extend(data["results"])
        total = data["paging"]["total"]
        offset += limit
        logger.info("Buscando IDs: %d/%d", len(all_ids), total)
        if offset >= total:
            break
    return all_ids


async def fetch_items_details(client: httpx.AsyncClient, item_ids: list[str]) -> list[dict]:
    """Busca detalhes em lote (20 por vez, limite da API)."""
    all_items = []
    for i in range(0, len(item_ids), 20):
        batch = item_ids[i:i+20]
        ids_str = ",".join(batch)
        resp = await client.get(f"{ML_API}/items", params={"ids": ids_str})
        resp.raise_for_status()
        for item_wrapper in resp.json():
            if item_wrapper.get("code") == 200:
                all_items.append(item_wrapper["body"])
            else:
                logger.warning("Erro ao buscar item: %s", item_wrapper.get("message", "?"))
        logger.info("Detalhes: %d/%d itens", len(all_items), len(item_ids))
    return all_items


async def fetch_competitors(client: httpx.AsyncClient, item_id: str) -> list[dict]:
    """Busca concorrentes de um produto via catalog ou search."""
    try:
        resp = await client.get(f"{ML_API}/items/{item_id}/product", timeout=10.0)
        if resp.status_code == 200:
            product_data = resp.json()
            buy_box = product_data.get("buy_box_winner", {})
            results = product_data.get("results", [])
            if not results and buy_box:
                results = [buy_box]
            return results[:10]
    except Exception:
        pass

    try:
        resp = await client.get(f"{ML_API}/items/{item_id}/competitors", timeout=10.0)
        if resp.status_code == 200:
            return resp.json().get("items", [])[:10]
    except Exception:
        pass

    return []


async def main():
    logger.info("=== IMPORTAÇÃO DE ANÚNCIOS DO MERCADO LIVRE ===")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        token = await get_access_token(db)
        logger.info("Token obtido: %s...", token[:20])

        async with httpx.AsyncClient(
            headers={"Authorization": f"Bearer {token}"},
            timeout=15.0,
        ) as client:
            user_resp = await client.get(f"{ML_API}/users/me")
            user_resp.raise_for_status()
            user = user_resp.json()
            user_id = str(user["id"])
            logger.info("Vendedor: %s (ID: %s)", user["nickname"], user_id)

            item_ids = await fetch_all_item_ids(client, user_id)
            logger.info("Total de anúncios encontrados: %d", len(item_ids))

            items = await fetch_items_details(client, item_ids)
            logger.info("Detalhes obtidos: %d itens", len(items))

            counts = {"products": 0, "listings": 0, "competitors": 0, "price_history": 0, "skipped": 0}

            for item in items:
                item_id = item["id"]
                title = item.get("title", "Sem título")
                price = float(item.get("price", 0))
                status = item.get("status", "unknown")

                if price == 0:
                    counts["skipped"] += 1
                    continue

                sku = item.get("seller_custom_field") or item_id
                category_id = item.get("category_id", "")
                permalink = item.get("permalink", "")
                listing_type = item.get("listing_type_id", "")
                free_shipping = item.get("shipping", {}).get("free_shipping", False)
                available_qty = item.get("available_quantity", 0)
                sold_qty = item.get("sold_quantity", 0)

                fee_pct = 16.0 if "gold" in listing_type else 11.0

                existing = await db.execute(
                    select(ProductListing).where(ProductListing.listing_id == item_id)
                )
                if existing.scalar_one_or_none():
                    counts["skipped"] += 1
                    continue

                product_result = await db.execute(
                    select(Product).where(Product.sku == sku)
                )
                product = product_result.scalar_one_or_none()

                if not product:
                    estimated_cost = round(price * 0.4, 2)
                    product = Product(
                        id=_uid(),
                        name=title,
                        sku=sku,
                        cost=estimated_cost,
                        current_price=price,
                        min_price=round(price * 0.7, 2),
                        max_price=round(price * 1.3, 2),
                        min_margin_pct=12.0,
                        target_margin_pct=25.0,
                        category=category_id,
                        brand=None,
                        keywords=title.lower(),
                        status="active" if status == "active" else "paused",
                    )
                    db.add(product)
                    counts["products"] += 1

                listing = ProductListing(
                    id=_uid(),
                    product_id=product.id,
                    marketplace="mercadolivre",
                    listing_id=item_id,
                    listing_url=permalink,
                    current_price=price,
                    listing_type=listing_type,
                    free_shipping=free_shipping,
                    status="active" if status == "active" else "paused",
                    marketplace_fee_pct=fee_pct,
                    avg_shipping_cost=0 if free_shipping else 15.0,
                )
                db.add(listing)
                counts["listings"] += 1

                competitors_data = await fetch_competitors(client, item_id)
                for comp_data in competitors_data:
                    comp_item_id = comp_data.get("id", comp_data.get("item_id", ""))
                    if comp_item_id == item_id:
                        continue

                    comp_price = float(comp_data.get("price", comp_data.get("sale_price", 0)))
                    comp_seller = comp_data.get("seller", {})
                    seller_name = comp_seller.get("nickname", "") if isinstance(comp_seller, dict) else str(comp_seller)

                    if comp_price <= 0:
                        continue

                    competitor = Competitor(
                        id=_uid(),
                        product_id=product.id,
                        marketplace="mercadolivre",
                        competitor_listing_id=comp_item_id,
                        competitor_seller=seller_name,
                        competitor_name=comp_data.get("title", title),
                        last_price=comp_price,
                        last_seen_at=datetime.utcnow(),
                        is_active=True,
                    )
                    db.add(competitor)
                    counts["competitors"] += 1

                    ph = CompetitorPriceHistory(
                        competitor_id=competitor.id,
                        product_id=product.id,
                        marketplace="mercadolivre",
                        price=comp_price,
                        free_shipping=comp_data.get("shipping", {}).get("free_shipping", False) if isinstance(comp_data.get("shipping"), dict) else False,
                        seller_name=seller_name,
                        collected_at=datetime.utcnow(),
                    )
                    db.add(ph)
                    counts["price_history"] += 1

                if counts["listings"] % 20 == 0:
                    logger.info("Progresso: %d produtos, %d listings, %d concorrentes", counts["products"], counts["listings"], counts["competitors"])

            await db.commit()

    logger.info("=== IMPORTAÇÃO COMPLETA ===")
    logger.info("Produtos criados:   %d", counts["products"])
    logger.info("Listings criados:   %d", counts["listings"])
    logger.info("Concorrentes:       %d", counts["competitors"])
    logger.info("Histórico preços:   %d", counts["price_history"])
    logger.info("Ignorados (dup/0):  %d", counts["skipped"])


if __name__ == "__main__":
    asyncio.run(main())
