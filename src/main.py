from typing import Optional
from uuid import UUID
from fastapi import FastAPI, Path, Query, Response

from src.models.enums import Status
from src.models.card import Card
from src.models.invoice import InvoiceRequest, InvoiceResponse
from src.config.settings import Settings
from src.services.invoice_service import InvoicingService
from src.services.health_check_service import HealthCheckService

app=FastAPI()
settings=Settings()
health_check_sevice = HealthCheckService(settings)
invoice_service = InvoicingService(settings)



@app.get("/health-check")
async def health_check(response: Response):
    response.status_code, json_response = await health_check_sevice.health_check()
    return json_response

     
@app.get("/invoice/{invoice_id}")
async def get_invoice(response: Response, invoice_id:UUID = Path(...)):
     response.status_code, json_response = await invoice_service.get_invoice(invoice_id)
     return json_response


@app.get("/invoices")
async def get_invoices(
        invoiceStatus: Optional[Status] = Query(None),
        limit: int = Query(10, ge=1, le=100),  # default 10, between 1 and 100
        offset: int = Query(0, ge=0)
):
    return await invoice_service.get_invoices(invoiceStatus, limit, offset)


@app.post("/invoice", response_model=InvoiceResponse)
async def create_invoice(response: Response, invoice_request: InvoiceRequest):
    response.status_code, json_response = await invoice_service.create_invoice(invoice_request)
    return json_response


@app.post("/invoice/pay/{invoice_id}", response_model=InvoiceResponse)
async def pay_invoice(
        response: Response,
        invoice_id:UUID = Path(...),
        card: Card = ...
):
    # For now, call invoice_service.pay_pending_invoice(invoice_id) as this is the requirement
    response.status_code, json_response = await invoice_service.pay_pending_invoice(invoice_id, card)
    return json_response