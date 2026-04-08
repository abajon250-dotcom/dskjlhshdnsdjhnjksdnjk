import aiohttp
from config import CRYPTOBOT_TOKEN

CRYPTO_API_URL = "https://pay.crypt.bot/api"

async def create_invoice(amount: float, currency: str = "USDT"):
    async with aiohttp.ClientSession() as session:
        headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
        data = {
            "asset": currency,
            "amount": str(amount),
        }
        async with session.post(f"{CRYPTO_API_URL}/createInvoice", headers=headers, data=data) as resp:
            result = await resp.json()
            if result.get("ok"):
                invoice_id = result["result"]["invoice_id"]
                pay_url = result["result"]["pay_url"]
                return invoice_id, pay_url
            else:
                raise Exception(f"CryptoBot error: {result}")

async def check_invoice_status(invoice_id: int) -> str:
    async with aiohttp.ClientSession() as session:
        headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
        params = {"invoice_ids": invoice_id}
        async with session.get(f"{CRYPTO_API_URL}/getInvoices", headers=headers, params=params) as resp:
            result = await resp.json()
            if result.get("ok") and result["result"]["items"]:
                return result["result"]["items"][0]["status"]
            else:
                return "unknown"