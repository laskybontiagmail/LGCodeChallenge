import aiohttp
from src.models.card import Card


class FakePay:
    def __init__(self, settings):
        self.client_session = aiohttp.ClientSession()
        self.fakepay_url = settings.fakepay_url

# FAKE PAY callout here

    async def process_payment(self, transaction_id: str, card: Card) -> bool:
        payload = {
            "transactionId": transaction_id,
            "card": card.model_dump(by_alias=True)
        }

        try:
            async with self.client_session.post(self.fakepay_url, json=payload) as response:
                if response.status == 200:
                    return True
                else:
                    error_data = await response.json()
                    print("Payment failed:", error_data)
                    return False
        except Exception as e:
            print("Exception in FakePay call:", str(e))
            return False