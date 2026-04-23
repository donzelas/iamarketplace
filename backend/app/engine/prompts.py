SYSTEM_PROMPT = """Você é um analista de e-commerce especializado em precificação dinâmica e gestão de anúncios patrocinados para marketplaces brasileiros (Mercado Livre, Shopee, Amazon, Magalu).

Sua função é analisar dados de mercado, margens e performance de ads, e recomendar ações para maximizar lucro mantendo competitividade.

REGRAS ABSOLUTAS (NUNCA VIOLE):
1. NUNCA recomende preços que resultem em margem abaixo do mínimo configurado
2. NUNCA aumente gastos com ads se o ACOS já está acima do máximo permitido
3. Priorize LUCRATIVIDADE sobre volume de vendas
4. Considere tendências: se concorrentes estão subindo preço, não precisa baixar
5. Ajustes de preço devem ser graduais (máximo 10% por ciclo, salvo emergência)
6. Se não tem dados suficientes, recomende HOLD (manter)

Responda SEMPRE em JSON válido com esta estrutura:
{
    "action": "ADJUST_PRICE|INCREASE_BID|REDUCE_BID|PAUSE_AD|INCREASE_BUDGET|REDUCE_BUDGET|HOLD",
    "new_price": <number ou null>,
    "new_bid": <number ou null>,
    "new_budget": <number ou null>,
    "reason": "<explicação curta e objetiva>",
    "confidence": <number entre 0 e 1>,
    "urgency": "low|medium|high|critical"
}"""


def build_analysis_prompt(product, market_analysis: dict, margin_data: dict, ad_performance: dict | None, config: dict) -> str:
    prompt = f"""
PRODUTO: {product.name} (SKU: {product.sku})
MARKETPLACE(S): {', '.join(market_analysis.get('marketplaces', {}).keys()) or 'N/A'}

== ANÁLISE DE MERCADO ==
Meu preço: R${market_analysis['my_price']:.2f}
Menor preço concorrente: R${market_analysis['price_stats']['min']:.2f}
Preço médio concorrentes: R${market_analysis['price_stats']['avg']:.2f}
Mediana concorrentes: R${market_analysis['price_stats']['median']:.2f}
Total concorrentes: {market_analysis['competitor_count']}
Minha posição: #{market_analysis['my_position']['rank']} de {market_analysis['my_position']['total']}
Gap vs menor preço: {market_analysis['price_gap']['vs_min_pct']:.1f}%
Gap vs preço médio: {market_analysis['price_gap']['vs_avg_pct']:.1f}%
Tendência de preço: {market_analysis['trend']['direction']} ({market_analysis['trend'].get('change_pct_72h', 0):.1f}% em 72h)
Concorrentes com frete grátis: {market_analysis['free_shipping_competitors']}

== MARGEM ATUAL ==
Preço de venda: R${margin_data['sale_price']:.2f}
Custo do produto: R${margin_data['cost']:.2f}
Taxa marketplace: R${margin_data['marketplace_fee']:.2f} ({margin_data['marketplace_fee_pct']:.1f}%)
Custo frete: R${margin_data['shipping_cost']:.2f}
Custo ads/venda: R${margin_data['ad_cost_per_sale']:.2f}
Custos totais: R${margin_data['total_costs']:.2f}
LUCRO LÍQUIDO: R${margin_data['net_profit']:.2f}
MARGEM: {margin_data['margin_pct']:.1f}%

CONFIGURAÇÕES:
- Margem mínima: {float(product.min_margin_pct)}%
- Margem alvo: {float(product.target_margin_pct)}%
- Preço mínimo permitido: R${float(product.min_price):.2f}
"""

    if market_analysis.get("marketplaces"):
        prompt += "\n== PREÇOS POR MARKETPLACE ==\n"
        for mp, stats in market_analysis["marketplaces"].items():
            prompt += f"  {mp}: min=R${stats['min']:.2f} avg=R${stats['avg']:.2f} max=R${stats['max']:.2f} ({stats['count']} anúncios)\n"

    if ad_performance:
        prompt += f"""
== PERFORMANCE DE ADS ==
Impressões: {ad_performance.get('impressions', 0):,}
Cliques: {ad_performance.get('clicks', 0):,}
Gasto total: R${ad_performance.get('spend', 0):.2f}
Pedidos via ads: {ad_performance.get('orders', 0)}
Receita via ads: R${ad_performance.get('revenue', 0):.2f}
CPC médio: R${ad_performance.get('cpc', 0):.2f}
CTR: {ad_performance.get('ctr', 0):.2f}%
Conversão: {ad_performance.get('conversion_rate', 0):.2f}%
ACOS: {ad_performance.get('acos', 0):.1f}%
ROAS: {ad_performance.get('roas', 0):.2f}x
ACOS máximo configurado: {config.get('max_acos', 30)}%
"""

    prompt += "\nCom base nesses dados, qual ação você recomenda? Responda em JSON."
    return prompt
