import pytest
from decimal import Decimal
from unittest.mock import MagicMock

from app.analysis.margin_calculator import MarginCalculator


@pytest.fixture
def calculator():
    return MarginCalculator()


@pytest.fixture
def product():
    p = MagicMock()
    p.cost = Decimal("50.00")
    p.min_margin_pct = Decimal("15.0")
    p.target_margin_pct = Decimal("25.0")
    p.current_price = Decimal("120.00")
    p.min_price = Decimal("80.00")
    return p


@pytest.fixture
def listing():
    l = MagicMock()
    l.current_price = Decimal("120.00")
    l.marketplace = "mercadolivre"
    l.marketplace_fee_pct = Decimal("0.16")
    l.avg_shipping_cost = Decimal("10.00")
    return l


def test_calculate_basic(calculator, product, listing):
    result = calculator.calculate(product, listing)

    assert result["sale_price"] == 120.00
    assert result["cost"] == 50.00
    assert result["marketplace_fee"] == 19.20  # 120 * 0.16
    assert result["shipping_cost"] == 10.00
    assert result["ad_cost_per_sale"] == 0.00
    assert result["total_costs"] == 79.20  # 50 + 19.20 + 10
    assert result["net_profit"] == 40.80  # 120 - 79.20
    assert result["margin_pct"] == 34.00  # 40.80 / 120 * 100


def test_calculate_with_ads(calculator, product, listing):
    ad_data = {"spend": 100.0, "orders": 10}
    result = calculator.calculate(product, listing, ad_data)

    assert result["ad_cost_per_sale"] == 10.00
    assert result["total_costs"] == 89.20
    assert result["net_profit"] == 30.80


def test_calculate_negative_margin(calculator, product, listing):
    listing.current_price = Decimal("60.00")
    result = calculator.calculate(product, listing)

    assert result["net_profit"] < 0
    assert result["margin_pct"] < 0


def test_simulate_price(calculator, product, listing):
    result = calculator.simulate_price(product, listing, 100.00)

    assert result["sale_price"] == 100.00
    assert listing.current_price == Decimal("120.00")  # original not changed


def test_min_price_for_margin(calculator, product, listing):
    min_price = calculator.min_price_for_margin(product, listing, 20.0)

    assert min_price > 0
    assert isinstance(min_price, float)

    listing.current_price = Decimal(str(min_price))
    result = calculator.calculate(product, listing)
    assert result["margin_pct"] >= 19.5  # ~20% with rounding


def test_default_fee_unknown_marketplace(calculator, product, listing):
    listing.marketplace = "unknown"
    listing.marketplace_fee_pct = None
    result = calculator.calculate(product, listing)

    assert result["marketplace_fee_pct"] == 15.0
