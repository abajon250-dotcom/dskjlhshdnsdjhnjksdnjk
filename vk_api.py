import aiohttp
class VKClient:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.api_version = "5.131"
        self.base_url = "https://api.vk.com/method/"
    async def _request(self, method: str, params: dict = None):
        if params is None: params = {}
        params["access_token"] = self.access_token
        params["v"] = self.api_version
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{self.base_url}{method}", params=params) as resp:
                data = await resp.json()
                if "error" in data:
                    raise Exception(f"VK API error: {data['error']['error_msg']}")
                return data.get("response")
    async def get_user_info(self):
        return await self._request("users.get")
    async def get_friends_count(self):
        resp = await self._request("friends.get", {"count": 1})
        return resp.get("count", 0)
    async def get_groups_count(self):
        resp = await self._request("groups.get", {"count": 1})
        return resp.get("count", 0)
    async def get_followers_count(self):
        resp = await self._request("users.getFollowers", {"count": 1})
        return resp.get("count", 0)
    async def get_friends_ids(self):
        resp = await self._request("friends.get", {"fields": ""})
        return resp.get("items", [])
    async def send_message(self, user_id: int, message: str):
        params = {"user_id": user_id, "message": message, "random_id": 0}
        return await self._request("messages.send", params)
    async def get_user_name(self, user_id: int):
        resp = await self._request("users.get", {"user_ids": user_id})
        if resp: return f"{resp[0]['first_name']} {resp[0]['last_name']}"
        return str(user_id)