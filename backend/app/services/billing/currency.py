"""Fixed conversion used only to compare legacy USD and new VND terms."""

from decimal import Decimal
from typing import Any

from app.core.errors import AppError
from app.models.billing import Plan

# Matches migration 0015; this is a catalog transition, not a live FX feed.
USD_VND_RATE = 26070


def replacement_event(plan: Plan, previous: dict[str, Any]) -> str:
    current_amount = Decimal(plan.price_monthly_minor_units)
    previous_amount = Decimal(previous["price_monthly_minor_units"])
    if plan.currency != previous["currency"]:
        if {plan.currency, previous["currency"]} != {"USD", "VND"}:
            raise AppError(
                409, "PLAN_CURRENCY_MISMATCH", "Plan currencies cannot be compared."
            )
        if plan.currency == "USD":
            current_amount = current_amount * USD_VND_RATE / 100
        else:
            previous_amount = previous_amount * USD_VND_RATE / 100
    return (
        "subscription_upgraded"
        if current_amount >= previous_amount
        else "subscription_downgraded"
    )
