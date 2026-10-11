"""Convert catalog USD cents to whole Vietnamese dong.

Revision ID: 0015_vnd_pricing
Revises: 0014_password_management

Pinned Vietcombank selling rate retrieved 2026-10-11: 26,070 VND/USD.
Existing subscription snapshots and audit history retain their original currency.
"""

from decimal import ROUND_HALF_UP, Decimal

import sqlalchemy as sa

from alembic import op

revision = "0015_vnd_pricing"
down_revision = "0014_password_management"
branch_labels = None
depends_on = None


def convert(source: str, target: str, multiplier: Decimal) -> None:
    plans = sa.table(
        "plans",
        sa.column("id", sa.Uuid()),
        sa.column("currency", sa.String()),
        sa.column("price_monthly_minor_units", sa.Integer()),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    connection = op.get_bind()
    rows = connection.execute(
        sa.select(plans).where(plans.c.currency == source).with_for_update()
    ).mappings()
    for row in rows:
        amount = int(
            (Decimal(row["price_monthly_minor_units"]) * multiplier).quantize(
                Decimal("1"), rounding=ROUND_HALF_UP
            )
        )
        if amount > 2147483647:
            raise RuntimeError("Converted Plan price exceeds signed 32-bit storage.")
        connection.execute(
            plans.update()
            .where(plans.c.id == row["id"])
            .values(
                currency=target,
                price_monthly_minor_units=amount,
                updated_at=sa.func.now(),
            )
        )


def upgrade() -> None:
    convert("USD", "VND", Decimal(26070) / 100)


def downgrade() -> None:
    # Reverse current catalog prices at the same fixed rate. Historical
    # snapshots and audit records are never rewritten in either direction.
    convert("VND", "USD", Decimal(100) / 26070)
