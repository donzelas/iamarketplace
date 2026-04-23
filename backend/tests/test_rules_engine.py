import pytest
from decimal import Decimal
from unittest.mock import MagicMock

from app.engine.rules import RulesEngine


@pytest.fixture
def config():
    return {
        "global_min_margin_pct": 10,
        "max_acos": 30,
        "max_price_change_pct": 10,
    }


@pytest.fixture
def engine(config):
    return RulesEngine(config)


@pytest.fixture
def product():
    p = MagicMock()
    p.sku = "TEST-001"
    p.min_margin_pct = Decimal("15.0")
    p.current_price = Decimal("100.00")
    p.min_price = Decimal("60.00")
    p.max_price = Decimal("200.00")
    return p


def test_negative_margin_triggers_emergency(engine, product):
    margin_data = {"margin_pct": -5.0, "total_costs": 110.0}
    decision = engine.check(product, margin_data, None)

    assert decision is not None
    assert decision["urgency"] == "critical"
    assert decision["new_price"] > 0


def test_below_global_min_triggers_price_raise(engine, product):
    margin_data = {"margin_pct": 8.0, "total_costs": 92.0}
    decision = engine.check(product, margin_data, None)

    assert decision is not None
    assert decision["action"] == "ADJUST_PRICE"
    assert decision["urgency"] == "critical"


def test_below_product_min_triggers_price_raise(engine, product):
    margin_data = {"margin_pct": 12.0, "total_costs": 88.0}
    decision = engine.check(product, margin_data, None)

    assert decision is not None
    assert decision["urgency"] == "high"


def test_healthy_margin_returns_none(engine, product):
    margin_data = {"margin_pct": 30.0, "total_costs": 70.0}
    decision = engine.check(product, margin_data, None)

    assert decision is None


def test_extreme_acos_pauses_ads(engine, product):
    margin_data = {"margin_pct": 25.0, "total_costs": 75.0}
    ad_data = {"acos": 50.0}
    decision = engine.check(product, margin_data, ad_data)

    assert decision is not None
    assert decision["action"] == "PAUSE_AD"


def test_high_acos_reduces_bid(engine, product):
    margin_data = {"margin_pct": 25.0, "total_costs": 75.0}
    ad_data = {"acos": 35.0}
    decision = engine.check(product, margin_data, ad_data)

    assert decision is not None
    assert decision["action"] == "REDUCE_BID"


def test_good_acos_returns_none(engine, product):
    margin_data = {"margin_pct": 25.0, "total_costs": 75.0}
    ad_data = {"acos": 20.0}
    decision = engine.check(product, margin_data, ad_data)

    assert decision is None


def test_validate_decision_caps_price_change(engine, product):
    decision = {"action": "ADJUST_PRICE", "new_price": 50.0, "reason": "test", "urgency": "medium"}
    validated = engine.validate_decision(decision, product, {"margin_pct": 20})

    assert validated["new_price"] == 90.0  # max 10% down from 100


def test_validate_decision_respects_min_price(engine, product):
    decision = {"action": "ADJUST_PRICE", "new_price": 40.0, "reason": "test", "urgency": "critical"}
    validated = engine.validate_decision(decision, product, {"margin_pct": 20})

    assert validated["new_price"] == 60.0  # min_price


def test_validate_decision_respects_max_price(engine, product):
    decision = {"action": "ADJUST_PRICE", "new_price": 300.0, "reason": "test", "urgency": "critical"}
    validated = engine.validate_decision(decision, product, {"margin_pct": 20})

    assert validated["new_price"] == 200.0  # max_price
