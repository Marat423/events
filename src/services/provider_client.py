import httpx
from datetime import date
from urllib.parse import urlparse, parse_qs
from typing import AsyncGenerator, Dict, Any

class ProviderClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    async def fetch_events(self, changed_at: date, cursor: str = None) -> Dict[str, Any]:
        url = f"{self.base_url}/api/events/"
        params = {"changed_at": changed_at.isoformat()}
        if cursor:
            params["cursor"] = cursor
        headers = {"x-api-key": self.api_key}
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def fetch_all_events(self, changed_at: date) -> AsyncGenerator[Dict, None]:
        cursor = None
        while True:
            data = await self.fetch_events(changed_at, cursor)
            for item in data.get("results", []):
                yield item
            if data.get("next"):

                parsed = urlparse(data["next"])
                cursor = parse_qs(parsed.query).get("cursor", [None])[0]
                if not cursor:
                    break
            else:
                break
