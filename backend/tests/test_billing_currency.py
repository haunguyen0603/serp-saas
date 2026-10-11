import pytest

from app.models.billing import Plan
from app.services.billing.currency import replacement_event


@pytest.mark.parametrize(
    "current,previous,expected",
    [
        (495330, 12900, "subscription_downgraded"),
        (3363030, 1900, "subscription_upgraded"),
        (495330, 1900, "subscription_upgraded"),
        (0, 1900, "subscription_downgraded"),
    ],
)
def test_legacy_usd_replacement_uses_equivalent_vnd_amounts(
    current, previous, expected
):
    plan = Plan(currency="VND", price_monthly_minor_units=current)
    assert (
        replacement_event(
            plan, {"currency": "USD", "price_monthly_minor_units": previous}
        )
        == expected
    )


def test_same_currency_replacement_still_compares_prices():
    assert (
        replacement_event(
            Plan(currency="VND", price_monthly_minor_units=495330),
            {"currency": "VND", "price_monthly_minor_units": 3363030},
        )
        == "subscription_downgraded"
    )
