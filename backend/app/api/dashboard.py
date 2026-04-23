from datetime import date, datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func as sqla_func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Product, ProductListing, Competitor, AdCampaign, AIDecision, AdPerformance, MarginSnapshot
from ..analysis import MarketAnalyzer

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


async def _get_product_ids_for_marketplace(db: AsyncSession, marketplace: str) -> list[str]:
    result = await db.execute(
        select(ProductListing.product_id).where(ProductListing.marketplace == marketplace).distinct()
    )
    return [r[0] for r in result.all()]


@router.get("/overview")
async def get_overview(marketplace: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    if marketplace:
        product_ids = await _get_product_ids_for_marketplace(db, marketplace)
        products_q = select(Product).where(Product.id.in_(product_ids))
    else:
        products_q = select(Product)

    active_result = await db.execute(products_q.where(Product.status == "active"))
    active_products = active_result.scalars().all()

    all_result = await db.execute(products_q)
    all_products = all_result.scalars().all()

    total_active = len(active_products)
    total_paused = len(all_products) - total_active

    total_value = sum(float(p.current_price or 0) for p in active_products)
    total_cost = sum(float(p.cost or 0) for p in active_products)
    avg_margin = ((total_value - total_cost) / total_value * 100) if total_value > 0 else 0

    pending_q = select(sqla_func.count(AIDecision.id)).where(AIDecision.status == "pending")
    if marketplace:
        pending_q = pending_q.where(AIDecision.product_id.in_(product_ids))
    pending_count = (await db.execute(pending_q)).scalar_one()

    today = date.today()
    spend_q = select(sqla_func.sum(AdPerformance.spend)).where(AdPerformance.date == today)
    revenue_q = select(sqla_func.sum(AdPerformance.revenue)).where(AdPerformance.date == today)
    if marketplace:
        spend_q = spend_q.where(AdPerformance.product_id.in_(product_ids))
        revenue_q = revenue_q.where(AdPerformance.product_id.in_(product_ids))
    total_spend = float((await db.execute(spend_q)).scalar_one() or 0)
    total_revenue = float((await db.execute(revenue_q)).scalar_one() or 0)

    listings_q = select(ProductListing)
    if marketplace:
        listings_q = listings_q.where(ProductListing.marketplace == marketplace)
    listings_result = await db.execute(listings_q)
    listings = listings_result.scalars().all()
    active_listings = sum(1 for l in listings if l.status == "active")
    paused_listings = sum(1 for l in listings if l.status != "active")

    categories: dict[str, int] = {}
    margin_health = {"healthy": 0, "warning": 0, "critical": 0}
    for p in active_products:
        cat = p.category or "Sem categoria"
        categories[cat] = categories.get(cat, 0) + 1
        cost = float(p.cost or 0)
        price = float(p.current_price or 0)
        margin = ((price - cost) / price * 100) if price > 0 else 0
        target = float(p.target_margin_pct or 25)
        minm = float(p.min_margin_pct or 15)
        if margin >= target:
            margin_health["healthy"] += 1
        elif margin >= minm:
            margin_health["warning"] += 1
        else:
            margin_health["critical"] += 1

    top_products = sorted(active_products, key=lambda p: float(p.current_price or 0), reverse=True)[:8]
    top_products_data = []
    for p in top_products:
        price = float(p.current_price or 0)
        cost = float(p.cost or 0)
        margin = ((price - cost) / price * 100) if price > 0 else 0
        top_products_data.append({
            "id": p.id, "name": p.name, "sku": p.sku,
            "price": round(price, 2), "cost": round(cost, 2),
            "margin": round(margin, 1), "status": p.status,
        })

    top_categories = sorted(categories.items(), key=lambda x: x[1], reverse=True)[:6]

    competitors_q = select(sqla_func.count(Competitor.id))
    if marketplace:
        competitors_q = competitors_q.where(Competitor.product_id.in_(product_ids))
    competitors_count = (await db.execute(competitors_q)).scalar_one()

    campaigns_q = select(sqla_func.count(AdCampaign.id))
    if marketplace:
        campaigns_q = campaigns_q.where(AdCampaign.product_id.in_(product_ids))
    campaigns_count = (await db.execute(campaigns_q)).scalar_one()

    return {
        "products": {"total": total_active + total_paused, "active": total_active, "paused": total_paused},
        "listings": {"total": len(listings), "active": active_listings, "paused": paused_listings},
        "competitors_count": competitors_count,
        "campaigns_count": campaigns_count,
        "today": {
            "ad_spend": round(total_spend, 2),
            "revenue": round(total_revenue, 2),
            "roas": round(total_revenue / max(total_spend, 0.01), 2) if total_spend > 0 else 0,
        },
        "financials": {
            "total_value": round(total_value, 2),
            "total_cost": round(total_cost, 2),
            "avg_margin": round(avg_margin, 1),
        },
        "margin_health": margin_health,
        "top_products": top_products_data,
        "categories": [{"name": name, "count": count} for name, count in top_categories],
        "pending_decisions": pending_count,
        "marketplace_filter": marketplace,
    }


@router.get("/marketplaces")
async def list_marketplaces(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(
            ProductListing.marketplace,
            sqla_func.count(ProductListing.id).label("listings"),
            sqla_func.count(sqla_func.distinct(ProductListing.product_id)).label("products"),
        ).group_by(ProductListing.marketplace)
    )
    rows = result.all()
    return [
        {"id": r[0], "name": _marketplace_name(r[0]), "listings": r[1], "products": r[2], "connected": True}
        for r in rows
    ] + [
        {"id": mp, "name": _marketplace_name(mp), "listings": 0, "products": 0, "connected": False}
        for mp in ["shopee", "amazon", "magalu"]
        if mp not in {r[0] for r in rows}
    ]


def _marketplace_name(key: str) -> str:
    names = {
        "mercadolivre": "Mercado Livre",
        "shopee": "Shopee",
        "amazon": "Amazon",
        "magalu": "Magalu",
    }
    return names.get(key.lower(), key.title())


@router.get("/product/{product_id}/analysis")
async def get_product_analysis(product_id: UUID, db: AsyncSession = Depends(get_db)):
    analyzer = MarketAnalyzer(db)
    return await analyzer.analyze_product(str(product_id))


@router.get("/product/{product_id}/margin-history")
async def get_margin_history(
    product_id: UUID,
    days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(MarginSnapshot)
        .where(MarginSnapshot.product_id == product_id)
        .where(MarginSnapshot.calculated_at >= since)
        .order_by(MarginSnapshot.calculated_at)
    )
    snapshots = result.scalars().all()

    return [
        {
            "sale_price": float(s.sale_price) if s.sale_price else None,
            "net_profit": float(s.net_profit) if s.net_profit else None,
            "margin_pct": float(s.margin_pct) if s.margin_pct else None,
            "health_status": s.health_status,
            "calculated_at": s.calculated_at.isoformat(),
        }
        for s in snapshots
    ]
