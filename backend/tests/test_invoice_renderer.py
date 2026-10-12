from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.schemas.invoice import InvoiceDetail, InvoiceTerms
from app.services import invoice_renderer


@pytest.mark.parametrize("status", list(invoice_renderer.STATUS_LABELS))
def test_invoice_pdf_unicode_status_and_escaped_fields(monkeypatch, status):
    paragraphs = []
    original = invoice_renderer.Paragraph

    def paragraph(value, style):
        paragraphs.append(value)
        return original(value, style)

    monkeypatch.setattr(invoice_renderer, "Paragraph", paragraph)
    now = datetime.now(UTC)
    invoice = InvoiceDetail(
        id=uuid4(),
        invoice_number="PAY_TEST",
        status=status,
        product_line="mobile",
        plan_code="mobile_starter",
        plan_name="Gói di động <Starter> & Nguyễn Hậu",
        amount_minor=1016730,
        currency="VND",
        provider="sepay",
        provider_environment="sandbox",
        created_at=now,
        paid_at=now if status == "paid" else None,
        account_email="buyer@example.test",
        payment_method="CARD",
        provider_order_id="a" * 200,
        provider_transaction_id="b" * 200,
        provider_transaction_uuid=None,
        updated_at=now,
        expires_at=now,
        cancelled_at=None,
        failed_at=None,
        terms=InvoiceTerms(
            billing_months=1,
            max_projects=3,
            max_keywords=200,
            monthly_keyword_checks=1000,
            scheduled_checks_enabled=False,
        ),
    )
    data = invoice_renderer.render_invoice_pdf(invoice)
    assert data.startswith(b"%PDF-") and data.rstrip().endswith(b"%%EOF")
    assert "Sandbox transaction — test environment." in paragraphs
    assert invoice_renderer.STATUS_LABELS[status] in paragraphs
    assert "Gói di động &lt;Starter&gt; &amp; Nguyễn Hậu" in paragraphs
    assert "1,016,730 VND" in paragraphs
    assert ("Payment confirmed by the payment provider." in paragraphs) == (
        status == "paid"
    )
    if status != "paid":
        assert any("It does not confirm a completed payment." in p for p in paragraphs)


def test_production_pdf_environment_and_missing_legacy_terms(monkeypatch):
    paragraphs = []
    original = invoice_renderer.Paragraph

    def paragraph(value, style):
        paragraphs.append(value)
        return original(value, style)

    monkeypatch.setattr(invoice_renderer, "Paragraph", paragraph)
    now = datetime.now(UTC)
    invoice = InvoiceDetail(
        id=uuid4(),
        invoice_number="PAY_PRODUCTION",
        status="paid",
        product_line="desktop",
        plan_code="desktop_pro",
        plan_name="Desktop Pro",
        amount_minor=2579550,
        currency="VND",
        provider="sepay",
        provider_environment="production",
        created_at=now,
        paid_at=now,
        account_email="buyer@example.test",
        payment_method=None,
        provider_order_id=None,
        provider_transaction_id=None,
        provider_transaction_uuid=None,
        updated_at=now,
        expires_at=now,
        cancelled_at=None,
        failed_at=None,
        terms=InvoiceTerms(),
    )
    assert invoice_renderer.render_invoice_pdf(invoice).startswith(b"%PDF-")
    assert "Production transaction." in paragraphs
    assert not any("Sandbox" in p for p in paragraphs)
