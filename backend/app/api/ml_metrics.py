"""Endpoints para métricas reais do Mercado Livre — usa API de Pedidos para dados por período."""
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import ProductListing, Product, SystemConfig

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/ml", tags=["Mercado Livre"])

ML_API = "https://api.mercadolibre.com"


async def _get_token(db: AsyncSession) -> Optional[str]:
    result = await db.execute(select(SystemConfig).where(SystemConfig.key == "ml_access_token"))
    config = result.scalar_one_or_none()
    return config.value["token"] if config else None


async def _get_user_id(client: httpx.AsyncClient) -> Optional[str]:
    try:
        resp = await client.get(f"{ML_API}/users/me")
        if resp.status_code == 200:
            return str(resp.json()["id"])
    except Exception:
        pass
    return None


# --------------- visits (paralelo) ---------------

async def _fetch_visit(client: httpx.AsyncClient, lid: str, days: int) -> tuple[str, int]:
    try:
        resp = await client.get(
            f"{ML_API}/items/{lid}/visits/time_window",
            params={"last": days, "unit": "day"},
        )
        if resp.status_code == 200:
            data = resp.json()
            return lid, sum(r.get("total", 0) for r in data.get("results", []))
    except Exception:
        pass
    return lid, -1


async def _fetch_all_visits(client: httpx.AsyncClient, listing_ids: list[str], days: int) -> dict[str, int]:
    visits: dict[str, int] = {}
    for i in range(0, len(listing_ids), 20):
        batch = listing_ids[i:i + 20]
        tasks = [_fetch_visit(client, lid, days) for lid in batch]
        results = await asyncio.gather(*tasks)
        for lid, v in results:
            if v >= 0:
                visits[lid] = v
        if i + 20 < len(listing_ids):
            await asyncio.sleep(0.3)
    return visits


# --------------- pedidos por período ---------------

async def _fetch_orders_for_period(
    client: httpx.AsyncClient, user_id: str, days: int,
) -> dict[str, dict]:
    """Busca pedidos reais da API do ML para o período.

    Retorna: { listing_id: { sold: int, revenue: float } }
    """
    date_to = datetime.now(timezone.utc)
    date_from = date_to - timedelta(days=days)

    orders_by_item: dict[str, dict] = {}
    offset = 0
    limit = 50
    total_orders = 0

    while True:
        try:
            resp = await client.get(
                f"{ML_API}/orders/search",
                params={
                    "seller": user_id,
                    "order.date_created.from": date_from.strftime("%Y-%m-%dT00:00:00.000-00:00"),
                    "order.date_created.to": date_to.strftime("%Y-%m-%dT23:59:59.999-00:00"),
                    "limit": limit,
                    "offset": offset,
                    "sort": "date_desc",
                },
            )
            if resp.status_code != 200:
                logger.warning("Orders API %d: %s", resp.status_code, resp.text[:300])
                break

            data = resp.json()
            results = data.get("results", [])

            for order in results:
                if order.get("status") == "cancelled":
                    continue
                total_orders += 1
                for oi in order.get("order_items", []):
                    lid = oi.get("item", {}).get("id", "")
                    if not lid:
                        continue
                    if lid not in orders_by_item:
                        orders_by_item[lid] = {"sold": 0, "revenue": 0.0}
                    qty = oi.get("quantity", 0)
                    price = oi.get("unit_price", 0)
                    orders_by_item[lid]["sold"] += qty
                    orders_by_item[lid]["revenue"] += qty * price

            paging = data.get("paging", {})
            total = paging.get("total", 0)

            if offset + limit >= total:
                break
            offset += limit
            await asyncio.sleep(0.1)

        except Exception as e:
            logger.warning("Orders fetch error: %s", e)
            break

    logger.info(
        "Orders API: %d itens com vendas, %d pedidos no período de %d dias",
        len(orders_by_item), total_orders, days,
    )
    return orders_by_item


# --------------- items batch (preço atual) ---------------

async def _fetch_items_batch(
    client: httpx.AsyncClient, listing_ids: list[str],
) -> dict[str, dict]:
    """Busca dados atuais dos items em batch (max 20 por request)."""
    items_map: dict[str, dict] = {}
    for i in range(0, len(listing_ids), 20):
        batch = listing_ids[i:i + 20]
        try:
            resp = await client.get(
                f"{ML_API}/items",
                params={"ids": ",".join(batch)},
            )
            if resp.status_code == 200:
                for wrapper in resp.json():
                    body = wrapper.get("body", {})
                    lid = body.get("id", "")
                    if lid:
                        shipping = body.get("shipping", {})
                        items_map[lid] = {
                            "price": body.get("price", 0),
                            "original_price": body.get("original_price"),
                            "sold_quantity": body.get("sold_quantity", 0),
                            "available_quantity": body.get("available_quantity", 0),
                            "status": body.get("status", ""),
                            "thumbnail": body.get("thumbnail", ""),
                            "free_shipping": shipping.get("free_shipping", False),
                            "listing_type": body.get("listing_type_id", ""),
                        }
        except Exception:
            pass
        if i + 20 < len(listing_ids):
            await asyncio.sleep(0.2)
    return items_map


# --------------- endpoints ---------------

@router.get("/listings")
async def list_ml_listings(
    status: str = "all",
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(ProductListing, Product.name, Product.cost, Product.sku)
        .join(Product, Product.id == ProductListing.product_id)
        .where(ProductListing.marketplace == "mercadolivre")
        .order_by(ProductListing.revenue_total.desc())
    )
    if status != "all":
        query = query.where(ProductListing.status == status)

    result = await db.execute(query)
    rows = result.all()

    token = await _get_token(db)
    visits_map: dict[str, int] = {}
    orders_map: dict[str, dict] = {}
    items_map: dict[str, dict] = {}

    if token:
        listing_ids = [l.listing_id for l, _, _, _ in rows]
        try:
            async with httpx.AsyncClient(
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0,
            ) as client:
                user_id = await _get_user_id(client)

                if user_id:
                    orders_map = await _fetch_orders_for_period(client, user_id, days)

                visits_map = await _fetch_all_visits(client, listing_ids, days)
                items_map = await _fetch_items_batch(client, listing_ids)

        except Exception as e:
            logger.warning("Erro ao buscar dados ML: %s", e)

    out = []
    for l, name, cost, sku in rows:
        lid = l.listing_id
        fresh = items_map.get(lid, {})
        order_data = orders_map.get(lid, {})
        visits = visits_map.get(lid, l.visits_total or 0)

        price = fresh.get("price", float(l.current_price))
        orig_price = fresh.get("original_price") or (float(l.original_price) if l.original_price else None)
        sold_period = order_data.get("sold", 0)
        revenue_period = round(order_data.get("revenue", 0.0), 2)
        sold_lifetime = fresh.get("sold_quantity", l.sold_quantity or 0)
        available = fresh.get("available_quantity", l.available_quantity or 0)
        thumb = fresh.get("thumbnail", l.thumbnail)
        free_ship = fresh.get("free_shipping", l.free_shipping)
        lt = fresh.get("listing_type", l.listing_type)
        item_status = fresh.get("status", l.status)

        out.append({
            "id": l.id,
            "listing_id": lid,
            "product_id": l.product_id,
            "product_name": name,
            "product_sku": sku,
            "product_cost": float(cost or 0),
            "thumbnail": thumb,
            "current_price": float(price),
            "original_price": float(orig_price) if orig_price else None,
            "listing_type": lt,
            "free_shipping": free_ship,
            "status": item_status,
            "sold_quantity": sold_lifetime,
            "sold_period": sold_period,
            "available_quantity": available,
            "visits_total": visits,
            "visits_period_days": days,
            "revenue_total": round(sold_lifetime * float(price), 2),
            "revenue_period": revenue_period,
            "marketplace_fee_pct": float(l.marketplace_fee_pct or 0),
            "condition": l.condition,
            "health": l.health,
            "listing_url": l.listing_url,
            "synced_at": l.synced_at.isoformat() if l.synced_at else None,
        })

    out.sort(key=lambda x: x["revenue_period"], reverse=True)
    return out


@router.get("/summary")
async def ml_summary(
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProductListing).where(ProductListing.marketplace == "mercadolivre")
    )
    listings = result.scalars().all()

    token = await _get_token(db)
    visits_map: dict[str, int] = {}
    orders_map: dict[str, dict] = {}

    if token:
        ids = [l.listing_id for l in listings]
        try:
            async with httpx.AsyncClient(
                headers={"Authorization": f"Bearer {token}"},
                timeout=30.0,
            ) as client:
                user_id = await _get_user_id(client)
                if user_id:
                    orders_map = await _fetch_orders_for_period(client, user_id, days)
                visits_map = await _fetch_all_visits(client, ids, days)
        except Exception:
            pass

    active = [l for l in listings if l.status == "active"]

    total_sold_period = sum(v.get("sold", 0) for v in orders_map.values())
    total_revenue_period = sum(v.get("revenue", 0.0) for v in orders_map.values())
    total_visits = sum(visits_map.get(l.listing_id, l.visits_total or 0) for l in listings)
    total_available = sum(l.available_quantity or 0 for l in listings)
    avg_price = sum(l.current_price for l in active) / len(active) if active else 0

    return {
        "total_listings": len(listings),
        "active_listings": len(active),
        "paused_listings": len(listings) - len(active),
        "total_revenue_period": round(total_revenue_period, 2),
        "total_sold_period": total_sold_period,
        "total_visits": total_visits,
        "total_available": total_available,
        "avg_price": round(avg_price, 2),
        "avg_price_per_sale": round(total_revenue_period / total_sold_period, 2) if total_sold_period > 0 else 0,
        "period_days": days,
    }
