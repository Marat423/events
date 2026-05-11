from collections.abc import AsyncGenerator
from datetime import date
from typing import Any
from urllib.parse import parse_qs, urlparse

import httpx


class ProviderClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def fetch_events(
        self,
        changed_at: date,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/api/events/"
        params = {"changed_at": changed_at.isoformat()}

        if cursor:
            params["cursor"] = cursor

        headers = {"x-api-key": self.api_key}

        async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            return response.json()

    async def fetch_all_events(
        self,
        changed_at: date,
    ) -> AsyncGenerator[dict[str, Any], None]:
        cursor = None

        while True:
            data = await self.fetch_events(changed_at=changed_at, cursor=cursor)

            for item in data.get("results", []):
                yield item

            next_url = data.get("next")

            if not next_url:
                break

            parsed = urlparse(next_url)
            cursor = parse_qs(parsed.query).get("cursor", [None])[0]

            if not cursor:
                break