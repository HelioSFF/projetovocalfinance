from decimal import Decimal

import pytest

from app.services.record_rules import (
    compute_amounts,
    failure_code,
    is_accepted,
    mentions_total,
    reconcile_type_category,
    resolve_prices,
)
from app.schemas.ai import DecisionResult, ExtractionResult


def make_decision(**overrides):
    data = {"plausible": 0.9, "is_financial": 0.9, "record_type": "expense", "category": "food"}
    data.update(overrides)
    return DecisionResult(**data)


def make_extraction(**overrides):
    data = {"item": "café", "quantity": 3, "unit_price": 5.0, "stated_total": 15.0}
    data.update(overrides)
    return ExtractionResult(**data)


def test_total_from_unit_price():
    quantity, unit_price, total = compute_amounts(3, 5.0, 15.0)
    assert (quantity, unit_price, total) == (Decimal("3.000"), Decimal("5.00"), Decimal("15.00"))


def test_total_from_stated_total_only():
    quantity, unit_price, total = compute_amounts(3, None, 30.0)
    assert (quantity, unit_price, total) == (Decimal("3.000"), Decimal("10.00"), Decimal("30.00"))


def test_stated_total_rounding_keeps_paid_total():
    quantity, unit_price, total = compute_amounts(3, None, 100.0)
    assert total == Decimal("100.00")
    assert unit_price == Decimal("33.33")


def test_compute_amounts_rejects_missing_prices():
    with pytest.raises(ValueError):
        compute_amounts(2, None, None)


def test_acceptance_requires_thresholds_and_prices():
    assert is_accepted(make_decision(), make_extraction(), 0.6) is True
    assert is_accepted(make_decision(plausible=0.5), make_extraction(), 0.6) is False
    assert is_accepted(make_decision(is_financial=None), make_extraction(), 0.6) is False
    assert is_accepted(make_decision(), make_extraction(item="  "), 0.6) is False
    assert is_accepted(make_decision(), make_extraction(quantity=0), 0.6) is False
    assert is_accepted(make_decision(), None, 0.6) is False
    assert is_accepted(make_decision(), make_extraction(unit_price=None, stated_total=None), 0.6) is False


def test_reconcile_swaps_mismatched_category():
    assert reconcile_type_category("expense", "salary") == ("expense", "other_expense")
    assert reconcile_type_category("income", "food") == ("income", "other_income")
    assert reconcile_type_category("expense", "food") == ("expense", "food")
    assert reconcile_type_category("income", "salary") == ("income", "salary")
    assert reconcile_type_category("expense", "unknown") == ("expense", "other_expense")
    assert reconcile_type_category(None, "food") == ("expense", "other_expense")


def test_resolve_prices_reads_unit_from_n_of_x_without_total_word():
    assert resolve_prices("desci três de dez conto", 3, None, 10.0) == (10.0, None)
    assert resolve_prices("três cafés de cinco reais", 3, 5.0, 15.0) == (5.0, 15.0)


def test_resolve_prices_keeps_stated_total_with_total_word():
    assert resolve_prices("gastei 100 em 3 cervejas", 3, None, 100.0) == (None, 100.0)
    assert resolve_prices("gastei 30 no mercado", 1, None, 30.0) == (None, 30.0)


def test_mentions_total_matches_words_not_substrings():
    assert mentions_total("gastei 30 em 3 cervejas") is True
    assert mentions_total("fechou tudo em 50") is True
    assert mentions_total("desci três de dez conto") is False
    assert mentions_total("três cafés de cinco reais") is False


def test_failure_code_distinguishes_cases():
    assert failure_code(make_decision(is_financial=0.2), 0.6) == "NOT_FINANCIAL"
    assert failure_code(make_decision(plausible=0.2, is_financial=0.1), 0.6) == "NOT_UNDERSTOOD"
    assert failure_code(make_decision(plausible=None, is_financial=None), 0.6) == "NOT_UNDERSTOOD"
