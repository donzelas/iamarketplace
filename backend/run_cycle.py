"""
Executa um ciclo completo de análise + decisão para um produto.

Uso:
    python run_cycle.py --sku SKU-001
    python run_cycle.py --all
    python run_cycle.py --sku SKU-001 --no-llm
"""
import argparse
import asyncio
import logging
import sys
from datetime import datetime, timedelta

from app.config import settings
from app.database import engine, async_session, Base
from app.models import Product, ProductListing, AdCampaign, AdPerformance, AIDecision
from app.analysis.market_analyzer import MarketAnalyzer
from app.analysis.margin_calculator import MarginCalculator
from app.engine.rules import RulesEngine
from app.engine.decision_engine import DecisionEngine
from app.engine.prompts import SYSTEM_PROMPT, build_analysis_prompt

from sqlalchemy import select, func as sqla_func

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("run_cycle")

SEPARATOR = "=" * 70


def print_section(title: str):
    print(f"\n{SEPARATOR}")
    print(f"  {title}")
    print(SEPARATOR)


async def get_ad_performance(db, product_id: str) -> dict | None:
    """Agrega performance de ads dos últimos 7 dias."""
    since = datetime.utcnow().date() - timedelta(days=7)
    result = await db.execute(
        select(
            sqla_func.sum(AdPerformance.impressions).label("impressions"),
            sqla_func.sum(AdPerformance.clicks).label("clicks"),
            sqla_func.sum(AdPerformance.spend).label("spend"),
            sqla_func.sum(AdPerformance.orders).label("orders"),
            sqla_func.sum(AdPerformance.revenue).label("revenue"),
        )
        .where(AdPerformance.product_id == product_id)
        .where(AdPerformance.date >= since)
    )
    row = result.one()
    if not row.impressions:
        return None

    impressions = int(row.impressions or 0)
    clicks = int(row.clicks or 0)
    spend = float(row.spend or 0)
    orders = int(row.orders or 0)
    revenue = float(row.revenue or 0)

    budget_result = await db.execute(
        select(sqla_func.avg(AdCampaign.daily_budget))
        .where(AdCampaign.product_id == product_id)
        .where(AdCampaign.status == "active")
    )
    daily_budget = float(budget_result.scalar_one_or_none() or 0)

    return {
        "impressions": impressions,
        "clicks": clicks,
        "spend": round(spend, 2),
        "orders": orders,
        "revenue": round(revenue, 2),
        "cpc": round(spend / max(clicks, 1), 2),
        "ctr": round(clicks / max(impressions, 1) * 100, 2),
        "conversion_rate": round(orders / max(clicks, 1) * 100, 2),
        "acos": round(spend / max(revenue, 0.01) * 100, 2),
        "roas": round(revenue / max(spend, 0.01), 2),
        "daily_budget": round(daily_budget, 2),
    }


async def get_past_decisions(db, product_id: str, limit: int = 5) -> list[dict]:
    result = await db.execute(
        select(AIDecision)
        .where(AIDecision.product_id == product_id)
        .order_by(AIDecision.created_at.desc())
        .limit(limit)
    )
    decisions = result.scalars().all()
    return [
        {
            "action": d.action,
            "reason": d.reason,
            "confidence": d.confidence,
            "status": d.status,
            "created_at": d.created_at.isoformat() if d.created_at else "?",
        }
        for d in decisions
    ]


async def run_for_product(db, product: Product, use_llm: bool = True):
    print_section(f"PRODUTO: {product.name} (SKU: {product.sku})")
    print(f"  Custo: R${product.cost:.2f}")
    print(f"  Preço atual: R${product.current_price:.2f}")
    print(f"  Faixa: R${product.min_price:.2f} — R${product.max_price:.2f}" if product.max_price else f"  Mínimo: R${product.min_price:.2f}")
    print(f"  Margem alvo: {product.target_margin_pct}% | Mínima: {product.min_margin_pct}%")

    # 1. Análise de mercado
    print_section("ANÁLISE DE MERCADO")
    analyzer = MarketAnalyzer(db)
    market = await analyzer.analyze_product(product.id)

    if market.get("status") in ("not_found", "no_data"):
        print(f"  ⚠ {market.get('status', 'sem dados')} — sem dados de concorrentes recentes")
        print("  Dica: conecte o Mercado Livre via /api/auth/mercadolivre/authorize para coletar dados reais")
        return

    stats = market["price_stats"]
    pos = market["my_position"]
    print(f"  Meu preço:    R${market['my_price']:.2f}")
    print(f"  Concorrentes: {market['competitor_count']}")
    print(f"  Faixa:        R${stats['min']:.2f} — R${stats['max']:.2f} (avg R${stats['avg']:.2f})")
    print(f"  Posição:      #{pos['rank']} de {pos['total']} (percentil {pos['percentile']})")
    print(f"  Tendência:    {market['trend']['direction']} ({market['trend'].get('change_pct_72h', 0):.1f}% 72h)")
    print(f"  Frete grátis: {market['free_shipping_competitors']} concorrentes")

    # 2. Cálculo de margem
    print_section("CÁLCULO DE MARGEM")
    listing_result = await db.execute(
        select(ProductListing)
        .where(ProductListing.product_id == product.id)
        .limit(1)
    )
    listing = listing_result.scalar_one_or_none()

    calc = MarginCalculator()
    ad_perf = await get_ad_performance(db, product.id)

    if listing:
        margin = calc.calculate(product, listing, ad_perf)
    else:
        margin = {
            "sale_price": float(product.current_price),
            "cost": float(product.cost),
            "marketplace_fee": round(float(product.current_price) * 0.16, 2),
            "marketplace_fee_pct": 16.0,
            "shipping_cost": 10.0,
            "ad_cost_per_sale": 3.0,
            "total_costs": 0,
            "net_profit": 0,
            "margin_pct": 0,
        }
        margin["total_costs"] = round(margin["cost"] + margin["marketplace_fee"] + margin["shipping_cost"] + margin["ad_cost_per_sale"], 2)
        margin["net_profit"] = round(margin["sale_price"] - margin["total_costs"], 2)
        margin["margin_pct"] = round(margin["net_profit"] / max(margin["sale_price"], 0.01) * 100, 2)

    print(f"  Preço venda:  R${margin['sale_price']:.2f}")
    print(f"  Custo prod.:  R${margin['cost']:.2f}")
    print(f"  Taxa MP:      R${margin['marketplace_fee']:.2f} ({margin['marketplace_fee_pct']:.1f}%)")
    print(f"  Frete:        R${margin['shipping_cost']:.2f}")
    print(f"  Ads/venda:    R${margin['ad_cost_per_sale']:.2f}")
    print(f"  Total custos: R${margin['total_costs']:.2f}")
    print(f"  LUCRO:        R${margin['net_profit']:.2f}")
    print(f"  MARGEM:       {margin['margin_pct']:.1f}%")

    # 3. Performance de Ads
    if ad_perf:
        print_section("PERFORMANCE DE ADS (7 dias)")
        print(f"  Impressões:  {ad_perf['impressions']:,}")
        print(f"  Cliques:     {ad_perf['clicks']:,}")
        print(f"  Gasto:       R${ad_perf['spend']:.2f}")
        print(f"  Pedidos:     {ad_perf['orders']}")
        print(f"  Receita:     R${ad_perf['revenue']:.2f}")
        print(f"  CPC:         R${ad_perf['cpc']:.2f}")
        print(f"  CTR:         {ad_perf['ctr']:.2f}%")
        print(f"  Conversão:   {ad_perf['conversion_rate']:.2f}%")
        print(f"  ACOS:        {ad_perf['acos']:.1f}%")
        print(f"  ROAS:        {ad_perf['roas']:.2f}x")

    # 4. Decisão da IA
    print_section("DECISÃO DA IA")

    config = {
        "llm_model": settings.llm_model,
        "max_acos": 30,
        "global_min_margin_pct": 10,
        "max_price_change_pct": 10,
    }

    rules = RulesEngine(config)
    past = await get_past_decisions(db, product.id)

    if use_llm and settings.openai_api_key:
        from openai import AsyncOpenAI
        llm_client = AsyncOpenAI(api_key=settings.openai_api_key)
        engine_inst = DecisionEngine(llm_client, rules, config)
        decision = await engine_inst.evaluate(product, market, margin, ad_perf)
    else:
        if not settings.openai_api_key:
            print("  [MODO OFFLINE] Sem OPENAI_API_KEY — usando apenas regras fixas")

        rule_decision = rules.check(product, margin, ad_perf)
        if rule_decision:
            decision = rule_decision
        else:
            prompt = build_analysis_prompt(product, market, margin, ad_perf, config, past)
            print("\n  [PROMPT que seria enviado à IA]:")
            for line in prompt.strip().split("\n"):
                print(f"    {line}")
            decision = {
                "action": "HOLD",
                "reason": "Modo offline — nenhuma regra de segurança ativada. Configure OPENAI_API_KEY para decisões com IA.",
                "confidence": 0.5,
                "urgency": "low",
                "source": "offline",
            }

    action_emoji = {
        "ADJUST_PRICE": "💰", "INCREASE_BID": "📈", "REDUCE_BID": "📉",
        "PAUSE_AD": "⏸️", "INCREASE_BUDGET": "💵", "REDUCE_BUDGET": "✂️", "HOLD": "⏹️",
    }
    emoji = action_emoji.get(decision.get("action", ""), "❓")

    print(f"\n  {emoji} AÇÃO: {decision.get('action', 'N/A')}")
    if decision.get("new_price"):
        print(f"  Novo preço: R${decision['new_price']:.2f}")
    if decision.get("new_bid"):
        print(f"  Novo bid: R${decision['new_bid']:.2f}")
    if decision.get("new_budget"):
        print(f"  Novo budget: R${decision['new_budget']:.2f}")
    print(f"  Motivo: {decision.get('reason', 'N/A')}")
    print(f"  Confiança: {decision.get('confidence', 0):.0%}")
    print(f"  Urgência: {decision.get('urgency', 'N/A')}")
    print(f"  Fonte: {decision.get('source', 'N/A')}")

    # 5. Salvar decisão no banco
    from app.models.models import new_uuid
    ai_dec = AIDecision(
        id=new_uuid(),
        product_id=product.id,
        decision_type="price_adjustment" if decision.get("new_price") else ("ad_budget" if decision.get("new_budget") or decision.get("new_bid") else "hold"),
        action=decision.get("action", "HOLD"),
        old_value=float(product.current_price),
        new_value=decision.get("new_price") or decision.get("new_budget") or decision.get("new_bid"),
        reason=decision.get("reason", ""),
        confidence=decision.get("confidence", 0),
        context={"source": decision.get("source", "unknown"), "market_analysis": {"position": pos["rank"], "competitor_count": market["competitor_count"]}},
        status="pending",
    )
    db.add(ai_dec)
    await db.flush()
    print(f"\n  ✅ Decisão salva no banco (id: {ai_dec.id[:8]}...)")

    print(f"\n{SEPARATOR}\n")


async def main():
    parser = argparse.ArgumentParser(description="Executa ciclo de análise + decisão da IA")
    parser.add_argument("--sku", type=str, help="SKU do produto para analisar (ex: SKU-001)")
    parser.add_argument("--all", action="store_true", help="Analisar todos os produtos ativos")
    parser.add_argument("--no-llm", action="store_true", help="Forçar modo offline (sem chamar OpenAI)")
    args = parser.parse_args()

    if not args.sku and not args.all:
        parser.print_help()
        print("\nExemplos:")
        print("  python run_cycle.py --sku SKU-001")
        print("  python run_cycle.py --all")
        print("  python run_cycle.py --sku SKU-003 --no-llm")
        return

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        use_llm = not args.no_llm

        if args.sku:
            result = await db.execute(select(Product).where(Product.sku == args.sku))
            product = result.scalar_one_or_none()
            if not product:
                print(f"\n  Produto com SKU '{args.sku}' nao encontrado.")
                print("  Cadastre produtos via API POST /api/products ou pelo dashboard")
                return
            await run_for_product(db, product, use_llm)

        elif args.all:
            result = await db.execute(select(Product).where(Product.status == "active"))
            products = result.scalars().all()
            if not products:
                print("\n  Nenhum produto ativo encontrado.")
                print("  Cadastre produtos via API POST /api/products ou pelo dashboard")
                return
            print(f"\n  Analisando {len(products)} produto(s)...\n")
            for product in products:
                await run_for_product(db, product, use_llm)

        await db.commit()

    print("✅ Ciclo finalizado com sucesso!")


if __name__ == "__main__":
    asyncio.run(main())
