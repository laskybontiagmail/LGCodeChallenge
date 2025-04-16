from typing import Optional, List
from uuid import UUID, uuid4

from fastapi import HTTPException

from src.models.card import MaskedCard, Card
from src.models.enums import Status
from src.models.invoice import InvoiceResponse, InvoiceRequest
from src.models.model_mappers import map_db_to_invoice_response
from src.db.invoice_manager_db import (
    get_joined_invoice_customer_by_id,
    save_invoice,
    get_all_invoices,
    update_invoice_status
)
from src.services.fake_pay_service import FakePay


class InvoicingService:
    def __init__(self, settings):
        self.fake_pay = FakePay(settings)

    async def get_invoice(self, invoice_id: UUID):
        invoice_customer = self._get_an_invoice(invoice_id, "No record found with this UUID")
        invoice_response: InvoiceResponse = map_db_to_invoice_response(invoice_customer[0], invoice_customer[1])
        return 200, invoice_response.model_dump(exclude_none=True, by_alias=True)

    async def get_invoices(
        self,
        invoiceStatus: Optional[Status] = None,
        limit: int = 10,
        offset: int = 0
    ):
        results = get_all_invoices(invoiceStatus, limit, offset)
        invoices: List[InvoiceResponse] = [
            map_db_to_invoice_response(invoice_retrieved, customer_retrieved)
            for invoice_retrieved, customer_retrieved in results
        ]
        return 200, [invoice.model_dump(exclude_none=True, by_alias=True) for invoice in invoices]

    async def create_invoice(self, invoice_request: InvoiceRequest):
        new_uuid = uuid4()
        new_str_id = str(new_uuid)

        save_invoice(invoice_request, new_str_id)

        if await self._make_payment(new_str_id, invoice_request.card):
            update_invoice_status(new_str_id, Status.PAID)

        invoice_response = self._finalize_invoice_response(
            new_uuid,
            f"Unable to retrieve the recently created Invoice with UUID: {new_str_id}",
            invoice_request.card
        )

        return 201, invoice_response.model_dump(exclude_none=True, by_alias=True)


    async def pay_pending_invoice(self, invoice_id: UUID, card: Card):
        invoice_retrieved, _ = self._get_an_invoice(
            invoice_id,
            f"Invoice to be paid with UUID: {invoice_id} Not Found"
        )

        if invoice_retrieved.invoice_status != Status.PENDING:
            raise HTTPException(status_code=409, detail=f"This Invoice: {invoice_id} is no longer PENDING")

        if await self._make_payment(str(invoice_id), card):
            update_invoice_status(str(invoice_id), Status.PAID)
        else:
            raise HTTPException(status_code=400, detail="Payment failed. Card was declined or invalid.")

        invoice_response = self._finalize_invoice_response(invoice_id, "Invoice not found", card)
        return 201, invoice_response.model_dump(exclude_none=True, by_alias=True)


    def _get_an_invoice(self, invoice_id: UUID, not_found_message: str):
        invoice_customer = get_joined_invoice_customer_by_id(invoice_id=str(invoice_id))
        if invoice_customer is None:
            raise HTTPException(status_code=404, detail=not_found_message)
        return invoice_customer


    async def _make_payment(self, transaction_id: str, card: Optional[Card]) -> bool:
        if not card:
            return False
        return await self.fake_pay.process_payment(transaction_id, card)


    def _finalize_invoice_response(
        self,
        invoice_id: UUID,
        not_found_message: str,
        card: Optional[Card] = None
    ) -> InvoiceResponse:
        invoice_retrieved, customer_retrieved = self._get_an_invoice(invoice_id, not_found_message)
        invoice_response: InvoiceResponse = map_db_to_invoice_response(invoice_retrieved, customer_retrieved)

        if card:
            invoice_response.card =self._mask_card_for_response(card)

        return invoice_response

    def _mask_card_for_response(self, card: Card) -> MaskedCard:
        clean_number = card.number.replace(" ", "")
        length = len(clean_number)

        if length <= 10:
            # Too short to mask meaningfully — mask all except last 4
            masked_number = "*" * (length - 4) + clean_number[-4:]
        else:
            first_six = clean_number[:6]
            last_four = clean_number[-4:]
            masked_middle = "*" * 8
            masked_number = f"{first_six}{masked_middle}{last_four}"

        return MaskedCard(
            number=masked_number,
            expiry=card.expiry,
            name=card.name
        )
