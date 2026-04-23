from datetime import datetime, date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


# ── Products ──

class ProductCreate(BaseModel):
    name: str
    sku: str
    cost: Decimal
    current_price: Decimal
    min_price: Decimal
    max_price: Decimal | None = None
    min_margin_pct: Decimal = Field(default=Decimal("15.0"))
    target_margin_pct: Decimal = Field(default=Decimal("25.0"))
    category: str | None = None
    brand: str | None = None
    keywords: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    cost: Decimal | None = None
    current_price: Decimal | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    min_margin_pct: Decimal | None = None
    target_margin_pct: Decimal | None = None
    category: str | None = None
    brand: str | None = None
    keywords: str | None = None
    status: str | None = None


class ProductResponse(BaseModel):
    id: UUID
    name: str
    sku: str
    cost: Decimal
    current_price: Decimal
    min_price: Decimal
    max_price: Decimal | None
    min_margin_pct: Decimal
    target_margin_pct: Decimal
    category: str | None
    brand: str | None
    keywords: str | None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Listings ──

class ListingCreate(BaseModel):
    product_id: UUID
    marketplace: str
    listing_id: str
    listing_url: str | None = None
    current_price: Decimal
    listing_type: str | None = None
    free_shipping: bool = False
    marketplace_fee_pct: Decimal | None = None
    avg_shipping_cost: Decimal = Decimal("0")


class ListingResponse(BaseModel):
    id: UUID
    product_id: UUID
    marketplace: str
    listing_id: str
    listing_url: str | None
    current_price: Decimal
    listing_type: str | None
    free_shipping: bool
    status: str
    marketplace_fee_pct: Decimal | None
    avg_shipping_cost: Decimal

    model_config = {"from_attributes": True}


# ── Competitors ──

class CompetitorData(BaseModel):
    marketplace: str
    listing_id: str | None = None
    title: str
    price: Decimal
    original_price: Decimal | None = None
    seller: str | None = None
    free_shipping: bool = False
    condition: str = "new"
    sold_quantity: int = 0
    url: str | None = None
    position: int | None = None
    collected_at: datetime | None = None


# ── Ads ──

class AdCampaignCreate(BaseModel):
    product_id: UUID
    platform: str
    campaign_id: str
    campaign_name: str | None = None
    campaign_type: str | None = None
    daily_budget: Decimal | None = None


class AdPerformanceData(BaseModel):
    platform: str
    date: date
    impressions: int = 0
    clicks: int = 0
    spend: Decimal = Decimal("0")
    orders: int = 0
    revenue: Decimal = Decimal("0")
    cpc: Decimal | None = None
    ctr: Decimal | None = None
    conversion_rate: Decimal | None = None
    acos: Decimal | None = None
    roas: Decimal | None = None


# ── Margin ──

class MarginData(BaseModel):
    sale_price: Decimal
    cost: Decimal
    marketplace_fee: Decimal
    marketplace_fee_pct: Decimal
    shipping_cost: Decimal
    ad_cost_per_sale: Decimal
    total_costs: Decimal
    net_profit: Decimal
    margin_pct: Decimal


# ── Market Analysis ──

class PriceStats(BaseModel):
    min: Decimal
    max: Decimal
    avg: Decimal
    median: Decimal
    stdev: Decimal


class PricePosition(BaseModel):
    rank: int
    total: int
    percentile: Decimal


class PriceTrend(BaseModel):
    direction: str
    avg_24h: Decimal | None = None
    avg_72h: Decimal | None = None
    avg_7d: Decimal | None = None
    change_pct_72h: Decimal | None = None


class MarketAnalysis(BaseModel):
    product_id: str
    product_name: str
    my_price: Decimal
    competitor_count: int
    price_stats: PriceStats
    my_position: PricePosition
    price_gap: dict
    free_shipping_competitors: int
    trend: PriceTrend
    marketplaces: dict
    analyzed_at: str


# ── AI Decisions ──

class DecisionResponse(BaseModel):
    id: UUID
    product_id: UUID
    decision_type: str
    action: str
    old_value: Decimal | None
    new_value: Decimal | None
    reason: str | None
    confidence: Decimal | None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Dashboard ──

class DashboardOverview(BaseModel):
    products: dict
    today: dict
    pending_decisions: int
    last_monitoring: datetime | None
