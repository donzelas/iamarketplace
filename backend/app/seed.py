"""
Popula o banco com dados fake para testar o sistema inteiro
sem precisar de API keys ou conexão com marketplaces.
"""
import random
import uuid
from datetime import datetime, timedelta, date

from sqlalchemy.ext.asyncio import AsyncSession

from .models import (
    Product,
    ProductListing,
    Competitor,
    CompetitorPriceHistory,
    AdCampaign,
    AdPerformance,
    MarginSnapshot,
    AIDecision,
)

PRODUCTS = [
    {
        "name": "Fone Bluetooth TWS Pro Max",
        "sku": "SKU-001",
        "cost": 35.00,
        "current_price": 89.90,
        "min_price": 69.90,
        "max_price": 129.90,
        "category": "Eletrônicos",
        "brand": "SoundMax",
        "keywords": "fone bluetooth tws sem fio wireless",
    },
    {
        "name": "Carregador Turbo USB-C 65W",
        "sku": "SKU-002",
        "cost": 22.00,
        "current_price": 59.90,
        "min_price": 44.90,
        "max_price": 79.90,
        "category": "Acessórios",
        "brand": "ChargePro",
        "keywords": "carregador turbo usb-c 65w rapido",
    },
    {
        "name": "Smartwatch Fitness Band 2024",
        "sku": "SKU-003",
        "cost": 48.00,
        "current_price": 149.90,
        "min_price": 119.90,
        "max_price": 199.90,
        "category": "Eletrônicos",
        "brand": "FitLife",
        "keywords": "smartwatch relogio inteligente fitness",
    },
    {
        "name": "Capa Silicone Premium iPhone 15",
        "sku": "SKU-004",
        "cost": 8.00,
        "current_price": 34.90,
        "min_price": 24.90,
        "max_price": 49.90,
        "category": "Acessórios",
        "brand": "CasePro",
        "keywords": "capa silicone iphone 15 proteção",
    },
    {
        "name": "Câmera IP WiFi 360° Full HD",
        "sku": "SKU-005",
        "cost": 55.00,
        "current_price": 169.90,
        "min_price": 129.90,
        "max_price": 219.90,
        "category": "Segurança",
        "brand": "SecureCam",
        "keywords": "camera ip wifi 360 segurança monitoramento",
    },
]

MARKETPLACES = ["mercadolivre", "shopee", "amazon"]

COMPETITOR_SELLERS = [
    "LojaTop BR", "MegaOferta Digital", "TechZone Store",
    "Bazar Express", "InfoShop Oficial", "ElectroMundo",
]

AD_PLATFORMS = ["mercado_ads", "shopee_ads", "google_ads"]


def _uid() -> str:
    return str(uuid.uuid4())


def _rand_price(base: float, var: float = 0.25) -> float:
    return round(base * (1 + random.uniform(-var, var)), 2)


async def run_seed(db: AsyncSession) -> dict:
    """Insere dados fake e retorna contadores."""
    now = datetime.utcnow()
    counts = {"products": 0, "listings": 0, "competitors": 0, "price_history": 0, "campaigns": 0, "ad_perf": 0, "margins": 0, "decisions": 0}

    for prod_data in PRODUCTS:
        product = Product(
            id=_uid(),
            name=prod_data["name"],
            sku=prod_data["sku"],
            cost=prod_data["cost"],
            current_price=prod_data["current_price"],
            min_price=prod_data["min_price"],
            max_price=prod_data["max_price"],
            min_margin_pct=15.0,
            target_margin_pct=25.0,
            category=prod_data["category"],
            brand=prod_data["brand"],
            keywords=prod_data["keywords"],
            status="active",
        )
        db.add(product)
        counts["products"] += 1

        for mp in MARKETPLACES:
            fee_pct = {"mercadolivre": 16.0, "shopee": 12.0, "amazon": 15.0}[mp]
            listing = ProductListing(
                id=_uid(),
                product_id=product.id,
                marketplace=mp,
                listing_id=f"MLB{random.randint(1000000, 9999999)}" if mp == "mercadolivre" else f"{mp.upper()}-{random.randint(100000, 999999)}",
                listing_url=f"https://{mp}.com.br/item/{product.sku}",
                current_price=_rand_price(prod_data["current_price"], 0.05),
                listing_type="classico" if mp == "mercadolivre" else "standard",
                free_shipping=random.choice([True, False]),
                status="active",
                marketplace_fee_pct=fee_pct,
                avg_shipping_cost=round(random.uniform(5, 20), 2),
            )
            db.add(listing)
            counts["listings"] += 1

        num_competitors = random.randint(3, 6)
        selected_sellers = random.sample(COMPETITOR_SELLERS, min(num_competitors, len(COMPETITOR_SELLERS)))

        for seller in selected_sellers:
            mp = random.choice(MARKETPLACES)
            comp_price = _rand_price(prod_data["current_price"], 0.30)
            competitor = Competitor(
                id=_uid(),
                product_id=product.id,
                marketplace=mp,
                competitor_listing_id=f"MLB{random.randint(1000000, 9999999)}",
                competitor_seller=seller,
                competitor_name=f"{prod_data['name']} - {seller}",
                last_price=comp_price,
                last_seen_at=now - timedelta(minutes=random.randint(10, 300)),
                is_active=True,
            )
            db.add(competitor)
            counts["competitors"] += 1

            for days_ago in range(14, -1, -1):
                collected = now - timedelta(days=days_ago, hours=random.randint(0, 12))
                drift = random.uniform(-0.03, 0.03) * days_ago
                hist_price = round(comp_price * (1 + drift), 2)
                ph = CompetitorPriceHistory(
                    competitor_id=competitor.id,
                    product_id=product.id,
                    marketplace=mp,
                    price=hist_price,
                    original_price=round(hist_price * random.uniform(1.0, 1.3), 2),
                    free_shipping=random.choice([True, False]),
                    seller_name=seller,
                    position_in_search=random.randint(1, 20),
                    collected_at=collected,
                )
                db.add(ph)
                counts["price_history"] += 1

        for platform in AD_PLATFORMS:
            campaign = AdCampaign(
                id=_uid(),
                product_id=product.id,
                platform=platform,
                campaign_id=f"CAMP-{platform.upper()}-{random.randint(10000, 99999)}",
                campaign_name=f"{prod_data['name'][:30]} - {platform}",
                campaign_type="sponsored_product",
                daily_budget=round(random.uniform(15, 80), 2),
                status="active",
            )
            db.add(campaign)
            counts["campaigns"] += 1

            for days_ago in range(14, -1, -1):
                d = date.today() - timedelta(days=days_ago)
                impressions = random.randint(500, 8000)
                ctr_val = random.uniform(0.8, 4.5)
                clicks = int(impressions * ctr_val / 100)
                cpc_val = round(random.uniform(0.15, 1.20), 2)
                spend = round(clicks * cpc_val, 2)
                conv_rate = random.uniform(1.5, 8.0)
                orders = max(1, int(clicks * conv_rate / 100))
                revenue = round(orders * prod_data["current_price"] * random.uniform(0.9, 1.1), 2)
                acos_val = round((spend / revenue) * 100, 2) if revenue > 0 else 0
                roas_val = round(revenue / spend, 2) if spend > 0 else 0

                perf = AdPerformance(
                    campaign_id=campaign.id,
                    product_id=product.id,
                    platform=platform,
                    date=d,
                    impressions=impressions,
                    clicks=clicks,
                    spend=spend,
                    orders=orders,
                    revenue=revenue,
                    cpc=cpc_val,
                    ctr=round(ctr_val, 2),
                    conversion_rate=round(conv_rate, 2),
                    acos=acos_val,
                    roas=roas_val,
                )
                db.add(perf)
                counts["ad_perf"] += 1

        sale_price = prod_data["current_price"]
        cost = prod_data["cost"]
        mp_fee = round(sale_price * 0.16, 2)
        ship = round(random.uniform(5, 15), 2)
        ad_cost = round(random.uniform(2, 8), 2)
        net = round(sale_price - cost - mp_fee - ship - ad_cost, 2)
        margin_pct = round((net / sale_price) * 100, 2)
        health = "healthy" if margin_pct >= 20 else ("warning" if margin_pct >= 10 else "critical")

        snap = MarginSnapshot(
            product_id=product.id,
            sale_price=sale_price,
            cost=cost,
            marketplace_fee=mp_fee,
            shipping_cost=ship,
            ad_cost_per_sale=ad_cost,
            net_profit=net,
            margin_pct=margin_pct,
            health_status=health,
        )
        db.add(snap)
        counts["margins"] += 1

        decision_scenarios = [
            ("price_adjustment", "reduce_price", sale_price, round(sale_price * 0.95, 2), "Concorrente principal baixou 5%. Recomendo acompanhar para manter posição.", 0.82),
            ("ad_budget", "increase_budget", 30.0, 45.0, "ROAS acima de 3x nos últimos 7 dias. Oportunidade de escalar.", 0.75),
        ]
        for dt, action, old_v, new_v, reason, conf in decision_scenarios:
            dec = AIDecision(
                id=_uid(),
                product_id=product.id,
                decision_type=dt,
                action=action,
                old_value=old_v,
                new_value=new_v,
                reason=reason,
                confidence=conf,
                context={"source": "seed", "marketplace": "mercadolivre"},
                status=random.choice(["pending", "pending", "approved"]),
            )
            db.add(dec)
            counts["decisions"] += 1

    await db.flush()
    return counts
