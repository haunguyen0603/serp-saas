import csv
import io
from collections.abc import Iterable, Mapping, Sequence
from datetime import datetime
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors  # type: ignore[import-untyped]
from reportlab.lib.enums import TA_CENTER  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
from reportlab.lib.styles import (  # type: ignore[import-untyped]
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import mm  # type: ignore[import-untyped]
from reportlab.pdfbase import pdfmetrics  # type: ignore[import-untyped]
from reportlab.pdfbase.ttfonts import TTFont  # type: ignore[import-untyped]
from reportlab.platypus import (  # type: ignore[import-untyped]
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

COMPARISON_CSV_COLUMNS = (
    "project_name",
    "device",
    "keyword",
    "keyword_id",
    "tracked_site_name",
    "tracked_site_id",
    "report_start_utc",
    "report_end_utc",
    "comparison_checked_at_utc",
    "comparison_position",
    "comparison_depth",
    "current_checked_at_utc",
    "current_position",
    "current_depth",
    "current_status",
    "movement_type",
    "numeric_change",
    "comparison_basis",
    "keyword_group",
    "keyword_tags",
)

HISTORY_CSV_COLUMNS = (
    "project_name",
    "device",
    "keyword",
    "keyword_id",
    "tracked_site_name",
    "tracked_site_id",
    "checked_at_utc",
    "position",
    "checked_depth",
    "status",
    "rank_check_id",
    "keyword_group",
    "keyword_tags",
)

_DANGEROUS_CSV_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def iso_utc(value: datetime | None) -> str:
    if value is None:
        return ""
    return value.isoformat().replace("+00:00", "Z")


def spreadsheet_safe(value: object) -> object:
    if isinstance(value, str) and value.startswith(_DANGEROUS_CSV_PREFIXES):
        return "'" + value
    return value


def render_csv(columns: Sequence[str], rows: Iterable[Mapping[str, object]]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=list(columns),
        extrasaction="ignore",
        lineterminator="\r\n",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({key: spreadsheet_safe(row.get(key, "")) for key in columns})
    return output.getvalue().encode("utf-8")


def _font_path() -> Path:
    candidates = (
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
        Path("/Library/Fonts/Arial Unicode.ttf"),
    )
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise RuntimeError("REPORT_FONT_UNAVAILABLE")


def _register_fonts() -> None:
    if "ReportUnicode" not in pdfmetrics.getRegisteredFontNames():
        path = _font_path()
        pdfmetrics.registerFont(TTFont("ReportUnicode", str(path)))


def _text(value: object) -> str:
    return escape("" if value is None else str(value))


def render_project_pdf(context: Mapping[str, Any]) -> bytes:
    _register_fonts()
    output = io.BytesIO()
    styles = getSampleStyleSheet()
    normal = ParagraphStyle(
        "ReportNormal",
        parent=styles["BodyText"],
        fontName="ReportUnicode",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155"),
    )
    heading = ParagraphStyle(
        "ReportHeading",
        parent=normal,
        fontSize=15,
        leading=19,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=10,
        spaceAfter=7,
        keepWithNext=True,
    )
    title = ParagraphStyle(
        "ReportTitle",
        parent=heading,
        fontSize=24,
        leading=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#2563eb"),
    )

    class NumberedDocTemplate(BaseDocTemplate):  # type: ignore[misc]
        def afterPage(self) -> None:  # noqa: N802
            canvas = self.canv
            canvas.saveState()
            canvas.setFont("ReportUnicode", 7)
            canvas.setFillColor(colors.HexColor("#64748b"))
            canvas.drawCentredString(A4[0] / 2, 10 * mm, f"Page {self.page}")
            canvas.restoreState()

    doc = NumberedDocTemplate(
        output,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=15 * mm,
        bottomMargin=18 * mm,
        title=str(context["project_name"]),
        author="SERP SaaS",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="report")
    doc.addPageTemplates([PageTemplate(id="report", frames=[frame])])
    story: list[Any] = [
        Paragraph("SERP SaaS · Ranking report", title),
        Spacer(1, 6 * mm),
        Paragraph(f"<b>Project:</b> {_text(context['project_name'])}", normal),
        Paragraph(
            f"<b>Environment:</b> Google · {_text(context['device']).title()}",
            normal,
        ),
        Paragraph(
            f"<b>Period:</b> {_text(context['period_start'])} — "
            f"{_text(context['period_end'])} (UTC)",
            normal,
        ),
        Paragraph(f"<b>Generated:</b> {_text(context['generated_at'])}", normal),
        Paragraph(
            "<b>Data as of:</b> "
            + _text(context.get("data_as_of") or "No successful observations"),
            normal,
        ),
        Paragraph(f"<b>Filters:</b> {_text(context['filter_label'])}", normal),
        Spacer(1, 5 * mm),
        Paragraph("Executive summary", heading),
    ]
    metrics = context["metrics"]
    kpis = [
        [
            "Distinct keywords",
            "Keyword × site pairs",
            "Observed pairs",
            "Checked depth",
        ],
        [
            str(metrics["distinct_keywords"]),
            str(metrics["keyword_site_pairs"]),
            str(metrics["observed_pairs"]),
            f"Top {metrics['effective_depth']}",
        ],
    ]
    kpi_table = Table(kpis, colWidths=[doc.width / 4] * 4)
    kpi_table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "ReportUnicode", 8),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f8fafc")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ]
        )
    )
    story.append(kpi_table)
    distribution = [["Bucket", "Pairs"]] + [
        [label, str(value)] for label, value in context["distribution_rows"]
    ]
    movements = [["Movement", "Pairs"]] + [
        [label, str(value)] for label, value in context["movement_rows"]
    ]
    for section_title, table_data in (
        ("Ranking distribution", distribution),
        ("Movement summary", movements),
    ):
        table = Table(table_data, colWidths=[doc.width * 0.72, doc.width * 0.28])
        table.setStyle(
            TableStyle(
                [
                    ("FONT", (0, 0), (-1, -1), "ReportUnicode", 8),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
                    ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.extend([Paragraph(section_title, heading), table, Spacer(1, 3 * mm)])

    story.append(Paragraph("Biggest winners and losers", heading))
    for label, rows in (
        ("Biggest winners", context["winners"]),
        ("Biggest losers", context["losers"]),
    ):
        data = [["Keyword", "Tracked site", "Previous", "Current", "Change"]]
        data.extend(
            [
                _text(row["keyword"]),
                _text(row["tracked_site_name"]),
                str(row["comparison_position"]),
                str(row["current_position"]),
                f"{int(row['numeric_change']):+d}",
            ]
            for row in rows
        )
        if len(data) == 1:
            story.append(
                Paragraph(f"<b>{label}:</b> No comparable numeric movements.", normal)
            )
            continue
        table = Table(
            data, repeatRows=1, colWidths=[55 * mm, 45 * mm, 22 * mm, 22 * mm, 20 * mm]
        )
        table.setStyle(
            TableStyle(
                [
                    ("FONT", (0, 0), (-1, -1), "ReportUnicode", 7),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(KeepTogether([Paragraph(label, normal), table, Spacer(1, 3 * mm)]))

    if metrics["keyword_site_pairs"] == 0:
        story.append(Paragraph("No matching Keywords.", heading))
    elif metrics["observed_pairs"] == 0:
        story.append(
            Paragraph("No ranking observations available for this period.", heading)
        )

    if context["include_details"]:
        story.append(Paragraph("Keyword details", heading))
        details = [["Keyword", "Tracked site", "Previous", "Current", "Movement"]]
        details.extend(
            [
                _text(row["keyword"]),
                _text(row["tracked_site_name"]),
                _text(row.get("comparison_position") or "—"),
                _text(row.get("current_position") or "—"),
                _text(row["movement_type"]),
            ]
            for row in context["details"]
        )
        table = Table(
            details,
            repeatRows=1,
            colWidths=[52 * mm, 43 * mm, 22 * mm, 22 * mm, 27 * mm],
        )
        table.setStyle(
            TableStyle(
                [
                    ("FONT", (0, 0), (-1, -1), "ReportUnicode", 6.7),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        story.append(table)
        if context["details_truncated"]:
            story.append(
                Paragraph(
                    "Keyword appendix was capped by the configured PDF detail limit. "
                    "Use Comparison CSV for the complete filtered result.",
                    normal,
                )
            )

    story.extend(
        [
            Paragraph("Methodology", heading),
            Paragraph(_text(context["methodology"]), normal),
        ]
    )
    doc.build(story)
    return output.getvalue()
