import asyncio
import re
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Query, Response

from app.dependencies.auth import CurrentUser, DBSession
from app.schemas.invoice import InvoiceDetail, InvoiceList, InvoiceStatus
from app.services.invoice_renderer import render_invoice_pdf
from app.services.invoices import InvoiceService

router = APIRouter(prefix="/billing/invoices", tags=["invoices"])


@router.get("")
async def invoices(
    user: CurrentUser,
    session: DBSession,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=1000)] = None,
    status: InvoiceStatus | None = None,
    product_line: Literal["desktop", "mobile"] | None = None,
    environment: Literal["sandbox", "production"] | None = None,
) -> InvoiceList:
    response.headers["Cache-Control"] = "private, no-store"
    return await InvoiceService(session).list_owned(
        user.id,
        limit=limit,
        cursor=cursor,
        status=status,
        product_line=product_line,
        environment=environment,
    )


@router.get("/{invoice_id}")
async def invoice(
    invoice_id: UUID, user: CurrentUser, session: DBSession, response: Response
) -> InvoiceDetail:
    response.headers["Cache-Control"] = "private, no-store"
    return await InvoiceService(session).detail(user, invoice_id)


@router.get(
    "/{invoice_id}/pdf",
    response_class=Response,
    responses={
        200: {
            "description": "Invoice PDF attachment",
            "content": {
                "application/pdf": {"schema": {"type": "string", "format": "binary"}}
            },
        }
    },
)
async def invoice_pdf(
    invoice_id: UUID, user: CurrentUser, session: DBSession
) -> Response:
    detail = await InvoiceService(session).detail(user, invoice_id)
    data = await asyncio.to_thread(render_invoice_pdf, detail)
    filename = re.sub(r"[^A-Za-z0-9_-]", "_", detail.invoice_number)
    return Response(
        content=data,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="invoice-{filename}.pdf"',
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )
