import pytest
import aiohttp
from uuid import uuid4


BASE_URL = "http://127.0.0.1:8000"

@pytest.mark.asyncio
async def test_health_check():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/health-check") as response:
            assert response.status == 200
            data = await response.json()
            assert "status" in data


@pytest.mark.asyncio
async def test_create_invoice():
    payload = {
        "jobDescription": "Test invoice",
        "customerId": 1,
        "amount": 100.00,
        "card": {
            "number": "1234567812345678",
            "expiry": "12-2025",
            "name": "Tony Stark"
        }
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/invoice", json=payload) as response:
            assert response.status == 201
            data = await response.json()
            assert data["jobDescription"] == payload["jobDescription"]
            assert data["invoiceStatus"] in ["PENDING", "PAID"]


@pytest.mark.asyncio
async def test_get_invoice_not_found():
    random_id = str(uuid4())
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/invoice/{random_id}") as response:
            assert response.status == 404


@pytest.mark.asyncio
async def test_get_invoices():
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{BASE_URL}/invoices") as response:
            assert response.status == 200
            data = await response.json()
            assert isinstance(data, list)


@pytest.mark.asyncio
async def test_pay_invoice():
    invoice_payload = {
        "jobDescription": "Pay later test",
        "customerId": 2,
        "amount": 500.00,
        "card": None
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{BASE_URL}/invoice", json=invoice_payload) as create_response:
            assert create_response.status == 201
            created_invoice = await create_response.json()
            invoice_id = created_invoice["id"]

        card_payload = {
            "number": "1234567812345678",
            "expiry": "12-2025",
            "name": "Steve Rogers"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{BASE_URL}/invoice/pay/{invoice_id}", json=card_payload) as pay_response:
                assert pay_response.status in [201, 400]
                pay_result = await pay_response.json()
                assert pay_result.get("id") == invoice_id
