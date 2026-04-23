from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Competitor, CompetitorPriceHistory

router = APIRouter(prefix="/api/competitors", tags=["Competitors"])


@router.get("/{product_id}")
async def list_competitors(product_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Competitor)
        .where(Competitor.product_id == product_id, Competitor.is_active.is_(True))
        .order_by(Competitor.last_price)
    )
    competitors = result.scalars().all()
    return [
        {
            "id": str(c.id),
            "marketplace": c.marketplace,
            "seller": c.competitor_seller,
            "name": c.competitor_name,
            "last_price": float(c.last_price) if c.last_price else None,
            "last_seen_at": c.last_seen_at.isoformat() if c.last_seen_at else None,
        }
        for c in competitors
    ]


@router.get("/{product_id}/price-history")
async def get_price_history(
    product_id: UUID,
    hours: int = Query(default=72, ge=1, le=720),
    marketplace: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    from datetime import datetime, timedelta

    since = datetime.utcnow() - timedelta(hours=hours)
    query = (
        select(CompetitorPriceHistory)
        .where(CompetitorPriceHistory.product_id == product_id)
        .where(CompetitorPriceHistory.collected_at >= since)
        .order_by(CompetitorPriceHistory.collected_at.desc())
    )

    if marketplace:
        query = query.where(CompetitorPriceHistory.marketplace == marketplace)

    result = await db.execute(query)
    prices = result.scalars().all()

    return [
        {
            "id": p.id,
            "competitor_id": str(p.competitor_id),
            "marketplace": p.marketplace,
            "price": float(p.price),
            "original_price": float(p.original_price) if p.original_price else None,
            "free_shipping": p.free_shipping,
            "seller": p.seller_name,
            "position": p.position_in_search,
            "collected_at": p.collected_at.isoformat(),
        }
        for p in prices
    ]
