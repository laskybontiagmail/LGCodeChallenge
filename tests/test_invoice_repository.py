import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from src.models.enums import Status
from src.models.invoice import InvoiceRequest
from src.db import invoice_manager_db
from src.config.settings import Settings


@pytest.fixture
def mock_db_session():
    settings = Settings()
    mock_db = MagicMock()
    with patch("src.db.invoice_manager_db.SessionLocal", return_value=mock_db):
        yield mock_db


def test_db_health_check(mock_db_session):
    mock_db_session.execute.return_value.scalar.return_value = True
    status_code, response = invoice_manager_db.db_health_check()
    assert status_code == 200
    assert response["status"] == "UP"


def test_get_joined_invoice_customer_by_id(mock_db_session):
    mock_db_session.query.return_value.join.return_value.filter.return_value.first.return_value = ("invoice", "customer")
    result = invoice_manager_db.get_joined_invoice_customer_by_id("some-id")
    assert result == ("invoice", "customer")


def test_get_all_invoices(mock_db_session):
    mock_db_session.query.return_value.join.return_value.order_by.return_value.limit.return_value.offset.return_value.all.return_value = [
        ("invoice1", "customer1"),
        ("invoice2", "customer2")
    ]
    results = invoice_manager_db.get_all_invoices()
    assert len(results) == 2


def test_save_invoice_success(mock_db_session):
    invoice_req = InvoiceRequest(
        job_description="Web App Dev",
        customer_id=1,
        amount=1299.99
    )
    invoice_id = str(uuid4())

    invoice = MagicMock()
    mock_db_session.refresh.return_value = invoice
    mock_db_session.commit.return_value = None
    mock_db_session.add.return_value = None
    mock_db_session.refresh.return_value = invoice

    with patch("src.db.invoice_manager_db.InvoiceDB", return_value=invoice):
        result = invoice_manager_db.save_invoice(invoice_req, invoice_id)
        assert result == invoice


def test_update_invoice_status_success(mock_db_session):
    invoice_mock = MagicMock()
    mock_db_session.query.return_value.filter.return_value.first.return_value = invoice_mock

    result = invoice_manager_db.update_invoice_status("some-id", Status.PAID)
    assert result is True
    assert invoice_mock.invoice_status == Status.PAID
