import uuid
from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import (
    String,
    Numeric,
    Boolean,
    Integer,
    Text,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    UniqueConstraint,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..database import Base


def new_uuid() -> str:
    return str(uuid.uuid4())


class Product(Base):
    __tablename__ = "products"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    sku: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    cost: Mapped[float] = mapped_column(Float, nullable=False)
    current_price: Mapped[float] = mapped_column(Float, nullable=False)
    min_price: Mapped[float] = mapped_column(Float, nullable=False)
    max_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_margin_pct: Mapped[float] = mapped_column(Float, nullable=False, default=15.0)
    target_margin_pct: Mapped[float] = mapped_column(Float, nullable=False, default=25.0)
    category: Mapped[str | None] = mapped_column(String(200), nullable=True)
    brand: Mapped[str | None] = mapped_column(String(200), nullable=True)
    keywords: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    listings: Mapped[list["ProductListing"]] = relationship(back_populates="product")
    competitors: Mapped[list["Competitor"]] = relationship(back_populates="product")
    campaigns: Mapped[list["AdCampaign"]] = relationship(back_populates="product")
    decisions: Mapped[list["AIDecision"]] = relationship(back_populates="product")


class ProductListing(Base):
    __tablename__ = "product_listings"
    __table_args__ = (UniqueConstraint("marketplace", "listing_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"))
    marketplace: Mapped[str] = mapped_column(String(50), nullable=False)
    listing_id: Mapped[str] = mapped_column(String(200), nullable=False)
    listing_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_price: Mapped[float] = mapped_column(Float, nullable=False)
    original_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    listing_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    free_shipping: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="active")
    marketplace_fee_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_shipping_cost: Mapped[float] = mapped_column(Float, default=0)

    sold_quantity: Mapped[int] = mapped_column(Integer, default=0)
    available_quantity: Mapped[int] = mapped_column(Integer, default=0)
    visits_total: Mapped[int] = mapped_column(Integer, default=0)
    visits_today: Mapped[int] = mapped_column(Integer, default=0)
    revenue_total: Mapped[float] = mapped_column(Float, default=0)
    conversion_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    health: Mapped[str | None] = mapped_column(String(50), nullable=True)
    thumbnail: Mapped[str | None] = mapped_column(Text, nullable=True)
    condition: Mapped[str | None] = mapped_column(String(20), nullable=True)

    synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    product: Mapped["Product"] = relationship(back_populates="listings")


class Competitor(Base):
    __tablename__ = "competitors"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"))
    marketplace: Mapped[str] = mapped_column(String(50), nullable=False)
    competitor_listing_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    competitor_seller: Mapped[str | None] = mapped_column(String(200), nullable=True)
    competitor_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    product: Mapped["Product"] = relationship(back_populates="competitors")
    price_history: Mapped[list["CompetitorPriceHistory"]] = relationship(back_populates="competitor")


class CompetitorPriceHistory(Base):
    __tablename__ = "competitor_price_history"
    __table_args__ = (
        Index("idx_comp_price_hist_product", "product_id", "collected_at"),
        Index("idx_comp_price_hist_competitor", "competitor_id", "collected_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    competitor_id: Mapped[str] = mapped_column(String(36), ForeignKey("competitors.id"))
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"))
    marketplace: Mapped[str] = mapped_column(String(50), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    original_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    free_shipping: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    seller_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    position_in_search: Mapped[int | None] = mapped_column(Integer, nullable=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    competitor: Mapped["Competitor"] = relationship(back_populates="price_history")


class AdCampaign(Base):
    __tablename__ = "ad_campaigns"
    __table_args__ = (UniqueConstraint("platform", "campaign_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"))
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    campaign_id: Mapped[str] = mapped_column(String(200), nullable=False)
    campaign_name: Mapped[str | None] = mapped_column(String(500), nullable=True)
    campaign_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    daily_budget: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    product: Mapped["Product"] = relationship(back_populates="campaigns")
    performance: Mapped[list["AdPerformance"]] = relationship(back_populates="campaign")


class AdPerformance(Base):
    __tablename__ = "ad_performance"
    __table_args__ = (
        UniqueConstraint("campaign_id", "date"),
        Index("idx_ad_perf_product_date", "product_id", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[str] = mapped_column(String(36), ForeignKey("ad_campaigns.id"))
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"))
    platform: Mapped[str] = mapped_column(String(50), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    spend: Mapped[float] = mapped_column(Float, default=0)
    orders: Mapped[int] = mapped_column(Integer, default=0)
    revenue: Mapped[float] = mapped_column(Float, default=0)
    cpc: Mapped[float | None] = mapped_column(Float, nullable=True)
    ctr: Mapped[float | None] = mapped_column(Float, nullable=True)
    conversion_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    acos: Mapped[float | None] = mapped_column(Float, nullable=True)
    roas: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    campaign: Mapped["AdCampaign"] = relationship(back_populates="performance")


class MarginSnapshot(Base):
    __tablename__ = "margin_snapshots"
    __table_args__ = (Index("idx_margin_snap_product", "product_id", "calculated_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"))
    sale_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    marketplace_fee: Mapped[float | None] = mapped_column(Float, nullable=True)
    shipping_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    ad_cost_per_sale: Mapped[float | None] = mapped_column(Float, nullable=True)
    net_profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    margin_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    health_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AIDecision(Base):
    __tablename__ = "ai_decisions"
    __table_args__ = (
        Index("idx_ai_decisions_product", "product_id", "created_at"),
        Index("idx_ai_decisions_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    product_id: Mapped[str] = mapped_column(String(36), ForeignKey("products.id"))
    decision_type: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    new_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    approved_by: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    product: Mapped["Product"] = relationship(back_populates="decisions")


class SystemConfig(Base):
    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())
