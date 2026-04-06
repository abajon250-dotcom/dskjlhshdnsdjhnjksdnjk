import aiohttp
import asyncio
from config import FIVESIM_TOKEN

BASE_URL = "https://5sim.net/v1"

async def rent_number(country: str = "russia", operator: str = "any", product: str = "telegram"):
    """Арендовать номер для продукта (telegram/vk)"""
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {FIVESIM_TOKEN}"}
        url = f"{BASE_URL}/user/buy/activation/{country}/{operator}/{product}"
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data
            else:
                text = await resp.text()
                raise Exception(f"5sim error: {resp.status} {text}")

async def check_order(order_id: str):
    """Проверить статус заказа и получить код"""
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {FIVESIM_TOKEN}"}
        url = f"{BASE_URL}/user/check/{order_id}"
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data
            else:
                return None

async def cancel_order(order_id: str):
    """Отменить заказ (если не удалось получить код)"""
    async with aiohttp.ClientSession() as session:
        headers = {"Authorization": f"Bearer {FIVESIM_TOKEN}"}
        url = f"{BASE_URL}/user/cancel/{order_id}"
        async with session.get(url, headers=headers) as resp:
            return resp.status == 200