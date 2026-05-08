from datetime import date
from typing import Any, AsyncGenerator, Dict

import httpx

from src.config import settings


class ProviderClient:
    BASE_URL = settings.CLIENT_HOST
    DEFAULT_PARAMS = {"changed_at": date(2000, 1, 1)}

    async def fetch_events(
        self, changed_at: date, api_key: str, cursor: str = None
    ) -> Dict[str, Any]:
        url = f"{self.BASE_URL}/api/events/"
        params = {"changed_at": changed_at.isoformat()}
        if cursor:
            params["cursor"] = cursor
        headers = {"x-api-key": api_key}
        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def fetch_all_events(
        self, changed_at: date, api_key: str
    ) -> AsyncGenerator[Dict, None]:

        cursor = None
        while True:
            data = await self.fetch_events(changed_at, api_key, cursor)
            for item in data.get("results", []):
                yield item
            if data.get("next"):
                from urllib.parse import parse_qs, urlparse

                parsed = urlparse(data["next"])
                cursor = parse_qs(parsed.query).get("cursor", [None])[0]
                if not cursor:
                    break
            else:
                break
