from decimal import Decimal


class MarginCalculator:
    MARKETPLACE_FEES = {
        "mercadolivre": {"classico": Decimal("0.11"), "premium": Decimal("0.16")},
        "shopee": {"normal": Decimal("0.14"), "mall": Decimal("0.08")},
        "amazon": {"fba": Decimal("0.15"), "fbm": Decimal("0.12")},
        "magalu": {"default": Decimal("0.16")},
    }

    def calculate(self, product, listing, ad_data: dict | None = None) -> dict:
        sale_price = Decimal(str(listing.current_price))
        cost = Decimal(str(product.cost))

        fee_pct = Decimal(str(listing.marketplace_fee_pct)) if listing.marketplace_fee_pct else self._default_fee(listing.marketplace)
        marketplace_fee = sale_price * fee_pct

        shipping = Decimal(str(listing.avg_shipping_cost or 0))

        ad_cost_per_sale = Decimal("0")
        if ad_data and ad_data.get("orders", 0) > 0:
            ad_cost_per_sale = Decimal(str(ad_data["spend"])) / Decimal(str(ad_data["orders"]))

        total_costs = cost + marketplace_fee + shipping + ad_cost_per_sale
        net_profit = sale_price - total_costs
        margin_pct = (net_profit / sale_price * 100) if sale_price > 0 else Decimal("0")

        return {
            "sale_price": float(round(sale_price, 2)),
            "cost": float(round(cost, 2)),
            "marketplace_fee": float(round(marketplace_fee, 2)),
            "marketplace_fee_pct": float(round(fee_pct * 100, 2)),
            "shipping_cost": float(round(shipping, 2)),
            "ad_cost_per_sale": float(round(ad_cost_per_sale, 2)),
            "total_costs": float(round(total_costs, 2)),
            "net_profit": float(round(net_profit, 2)),
            "margin_pct": float(round(margin_pct, 2)),
        }

    def simulate_price(self, product, listing, new_price: float, ad_data: dict | None = None) -> dict:
        """Simula margem com um novo preço sem alterar o produto."""
        original = listing.current_price
        listing.current_price = Decimal(str(new_price))
        result = self.calculate(product, listing, ad_data)
        listing.current_price = original
        return result

    def min_price_for_margin(self, product, listing, target_margin_pct: float, ad_data: dict | None = None) -> float:
        """Calcula o preço mínimo necessário para atingir a margem alvo."""
        cost = Decimal(str(product.cost))
        fee_pct = Decimal(str(listing.marketplace_fee_pct)) if listing.marketplace_fee_pct else self._default_fee(listing.marketplace)
        shipping = Decimal(str(listing.avg_shipping_cost or 0))

        ad_cost = Decimal("0")
        if ad_data and ad_data.get("orders", 0) > 0:
            ad_cost = Decimal(str(ad_data["spend"])) / Decimal(str(ad_data["orders"]))

        fixed_costs = cost + shipping + ad_cost
        target = Decimal(str(target_margin_pct)) / Decimal("100")

        denominator = Decimal("1") - fee_pct - target
        if denominator <= 0:
            return float("inf")

        min_price = fixed_costs / denominator
        return float(round(min_price, 2))

    def _default_fee(self, marketplace: str) -> Decimal:
        fees = self.MARKETPLACE_FEES.get(marketplace, {})
        if fees:
            return list(fees.values())[0]
        return Decimal("0.15")
