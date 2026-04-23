from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import AdCampaign, AdPerformance
from ..schemas import AdCampaignCreate

router = APIRouter(prefix="/api/ads", tags=["Ads"])


@router.get("/campaigns")
async def list_campaigns(
    product_id: UUID | None = None,
    platform: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(AdCampaign).where(AdCampaign.status == "active")
    if product_id:
        query = query.where(AdCampaign.product_id == product_id)
    if platform:
        query = query.where(AdCampaign.platform == platform)

    result = await db.execute(query.order_by(AdCampaign.campaign_name))
    campaigns = result.scalars().all()

    return [
        {
            "id": str(c.id),
            "product_id": str(c.product_id),
            "platform": c.platform,
            "campaign_id": c.campaign_id,
            "campaign_name": c.campaign_name,
            "daily_budget": float(c.daily_budget) if c.daily_budget else None,
            "status": c.status,
        }
        for c in campaigns
    ]


@router.post("/campaigns", status_code=201)
async def create_campaign(data: AdCampaignCreate, db: AsyncSession = Depends(get_db)):
    campaign = AdCampaign(**data.model_dump())
    db.add(campaign)
    await db.flush()
    await db.refresh(campaign)
    return {"id": str(campaign.id), "status": "created"}


@router.get("/performance/{product_id}")
async def get_ad_performance(
    product_id: UUID,
    days: int = Query(default=7, ge=1, le=90),
    platform: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    from datetime import date, timedelta

    since = date.today() - timedelta(days=days)
    query = (
        select(AdPerformance)
        .where(AdPerformance.product_id == product_id)
        .where(AdPerformance.date >= since)
    )
    if platform:
        query = query.where(AdPerformance.platform == platform)

    result = await db.execute(query.order_by(AdPerformance.date.desc()))
    performances = result.scalars().all()

    return [
        {
            "platform": p.platform,
            "date": p.date.isoformat(),
            "impressions": p.impressions,
            "clicks": p.clicks,
            "spend": float(p.spend),
            "orders": p.orders,
            "revenue": float(p.revenue),
            "cpc": float(p.cpc) if p.cpc else None,
            "ctr": float(p.ctr) if p.ctr else None,
            "conversion_rate": float(p.conversion_rate) if p.conversion_rate else None,
            "acos": float(p.acos) if p.acos else None,
            "roas": float(p.roas) if p.roas else None,
        }
        for p in performances
    ]
