import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from src.models.enums import Status
from src.models.card import Card
from src.services.invoice_service import InvoicingService
from src.config.settings import Settings


@pytest.fixture
def invoice_service():
    settings = Settings()
    with patch("src.services.invoice_service.FakePay") as MockFakePay:
        mock_fakepay = MockFakePay.return_value
        mock_fakepay.process_payment = AsyncMock(return_value=True)

        service = InvoicingService(settings)
        service._get_an_invoice = MagicMock()
        service._finalize_invoice_response = MagicMock()
        return service


def test_mask_card_for_response(invoice_service):
    card = Card(
        number="1234567890123456",
        expiry="12-2025",
        name="Tony Stark"
    )
    masked = invoice_service._mask_card_for_response(card)
    assert masked.number == "123456********3456"
    assert masked.expiry == card.expiry
    assert masked.name == card.name


@pytest.mark.asyncio
async def test_make_payment_success(invoice_service):
    card = Card(
        number="1234567890123456",
        expiry="12-2025",
        name="Tony Stark"
    )
    result = await invoice_service._make_payment("test-id", card)
    assert result is True
    invoice_service.fake_pay.process_payment.assert_awaited_once()


@pytest.mark.asyncio
async def test_make_payment_skips_on_none(invoice_service):
    result = await invoice_service._make_payment("test-id", None)
    assert result is False
    invoice_service.fake_pay.process_payment.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_an_invoice_not_found():
    service = InvoicingService(Settings())
    fake_id = uuid4()

    from src.db.invoice_manager_db import get_joined_invoice_customer_by_id

    original_fn = get_joined_invoice_customer_by_id
    try:
        def fake_get(invoice_id: str):
            return None

        import src.db.invoice_manager_db
        src.db.invoice_manager_db.get_joined_invoice_customer_by_id = fake_get

        with pytest.raises(HTTPException) as e:
            service._get_an_invoice(fake_id, "Invoice not found")

        assert e.value.status_code == 404

    finally:
        src.db.invoice_manager_db.get_joined_invoice_customer_by_id = original_fn


@pytest.mark.asyncio
async def test_pay_pending_invoice_success(invoice_service):
    mock_invoice = MagicMock()
    mock_invoice.invoice_status = Status.PENDING
    invoice_service._get_an_invoice.return_value = (mock_invoice, MagicMock())

    card = Card(number="1234567890123456", expiry="12-2025", name="Tony Stark")
    invoice_service._finalize_invoice_response.return_value = MagicMock()

    response = await invoice_service.pay_pending_invoice(uuid4(), card)
    assert response[0] == 201
    invoice_service._finalize_invoice_response.assert_called_once()


@pytest.mark.asyncio
async def test_pay_pending_invoice_conflict(invoice_service):
    mock_invoice = MagicMock()
    mock_invoice.invoice_status = Status.PAID
    invoice_service._get_an_invoice.return_value = (mock_invoice, MagicMock())

    card = Card(number="1234567890123456", expiry="12-2025", name="Tony Stark")

    with pytest.raises(Exception) as e:
        await invoice_service.pay_pending_invoice(uuid4(), card)

    assert e.value.status_code == 409
