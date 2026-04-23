from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func as sqla_func
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import Product, AIDecision, AdPerformance, MarginSnapshot
from ..analysis import MarketAnalyzer

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/overview")
async def get_overview(db: AsyncSession = Depends(get_db)):
    products_result = await db.execute(select(Product).where(Product.status == "active"))
    products = products_result.scalars().all()

    total = len(products)

    pending_result = await db.execute(
        select(sqla_func.count(AIDecision.id)).where(AIDecision.status == "pending")
    )
    pending_count = pending_result.scalar_one()

    from datetime import date, timedelta
    today = date.today()

    spend_result = await db.execute(
        select(sqla_func.sum(AdPerformance.spend)).where(AdPerformance.date == today)
    )
    total_spend = float(spend_result.scalar_one() or 0)

    revenue_result = await db.execute(
        select(sqla_func.sum(AdPerformance.revenue)).where(AdPerformance.date == today)
    )
    total_revenue = float(revenue_result.scalar_one() or 0)

    return {
        "products": {"total": total, "active": total},
        "today": {
            "ad_spend": round(total_spend, 2),
            "revenue": round(total_revenue, 2),
            "roas": round(total_revenue / max(total_spend, 0.01), 2),
        },
        "pending_decisions": pending_count,
    }


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
    from datetime import datetime, timedelta
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
