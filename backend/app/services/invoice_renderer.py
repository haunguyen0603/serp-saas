import io
from datetime import UTC, datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
from reportlab.lib.styles import ParagraphStyle  # type: ignore[import-untyped]
from reportlab.lib.units import mm  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.schemas.invoice import InvoiceDetail
from app.services.report_renderers import _register_fonts

STATUS_LABELS = {
    "pending": "Pending payment",
    "checkout_created": "Awaiting payment",
    "paid": "Paid",
    "failed": "Failed",
    "cancelled": "Cancelled",
    "voided": "Voided",
    "expired": "Expired",
    "review_required": "Needs review",
}


def render_invoice_pdf(invoice: InvoiceDetail) -> bytes:
    _register_fonts()
    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=f"Invoice {invoice.invoice_number}",
        author="SERP SaaS",
    )
    normal = ParagraphStyle(
        "InvoiceBody",
        fontName="ReportUnicode",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334155"),
        splitLongWords=True,
    )
    heading = ParagraphStyle(
        "InvoiceHeading",
        parent=normal,
        fontSize=22,
        leading=28,
        spaceAfter=12,
        textColor=colors.HexColor("#0f172a"),
    )
    section = ParagraphStyle(
        "InvoiceSection", parent=normal, fontSize=11, leading=15, keepWithNext=True
    )

    def text(value: object) -> Paragraph:
        return Paragraph(escape(str(value)) if value is not None else "—", normal)

    def date(value: datetime | None) -> str:
        return value.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC") if value else "—"

    def table(rows: list[tuple[str, object]]) -> Table:
        result = Table(
            [[text(label), text(value)] for label, value in rows],
            colWidths=[doc.width * 0.34, doc.width * 0.66],
            hAlign="LEFT",
        )
        result.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return result

    terms = invoice.terms
    notice = (
        "Sandbox transaction — test environment."
        if invoice.provider_environment == "sandbox"
        else "Production transaction."
    )
    confirmation = (
        "Payment confirmed by the payment provider."
        if invoice.status == "paid"
        else "This document records the current transaction status. "
        "It does not confirm a completed payment."
    )
    doc.build(
        [
            Paragraph("SERP SaaS · Invoice", heading),
            text(invoice.invoice_number),
            Spacer(1, 5 * mm),
            text(notice),
            text(confirmation),
            Spacer(1, 6 * mm),
            table(
                [
                    ("Status", STATUS_LABELS[invoice.status]),
                    ("Account", invoice.account_email),
                    ("Plan", invoice.plan_name),
                    ("Product line", invoice.product_line.title()),
                    ("Amount", f"{invoice.amount_minor:,} {invoice.currency}"),
                    (
                        "Billing duration",
                        f"{terms.billing_months} month(s)"
                        if terms.billing_months
                        else "—",
                    ),
                    ("Created", date(invoice.created_at)),
                    ("Paid", date(invoice.paid_at)),
                    ("Checkout expires", date(invoice.expires_at)),
                    ("Cancelled", date(invoice.cancelled_at)),
                    ("Failed", date(invoice.failed_at)),
                    ("Last updated", date(invoice.updated_at)),
                ]
            ),
            Spacer(1, 6 * mm),
            Paragraph("Transaction details", section),
            Spacer(1, 2 * mm),
            table(
                [
                    ("Provider", invoice.provider),
                    ("Environment", invoice.provider_environment.title()),
                    ("Payment method", invoice.payment_method),
                    ("Provider order", invoice.provider_order_id),
                    ("Transaction reference", invoice.provider_transaction_id),
                    ("Transaction UUID", invoice.provider_transaction_uuid),
                ]
            ),
            Spacer(1, 6 * mm),
            Paragraph("Plan terms at checkout", section),
            Spacer(1, 2 * mm),
            table(
                [
                    ("Projects", terms.max_projects),
                    ("Keywords", terms.max_keywords),
                    ("Checks per month", terms.monthly_keyword_checks),
                    (
                        "Scheduled checks",
                        terms.max_scheduled_frequency
                        if terms.scheduled_checks_enabled
                        else "Not included"
                        if terms.scheduled_checks_enabled is False
                        else "—",
                    ),
                ]
            ),
            Spacer(1, 5 * mm),
            text(f"Exported {date(datetime.now(UTC))}"),
        ]
    )
    return output.getvalue()
