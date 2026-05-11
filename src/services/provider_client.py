import asyncio
import logging
from datetime import date
from typing import Any, AsyncGenerator, Dict, Optional
from urllib.parse import parse_qs, urlparse

import httpx

logger = logging.getLogger(__name__)


class ProviderClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    async def fetch_events(
        self,
        changed_at: date,
        cursor: Optional[str] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/events/"
        params = {"changed_at": changed_at.isoformat()}

        if cursor:
            params["cursor"] = cursor

        headers = {"x-api-key": self.api_key}

        for attempt in range(3):
            try:
                async with httpx.AsyncClient(
                    follow_redirects=True,
                    timeout=30.0,
                ) as client:
                    resp = await client.get(url, params=params, headers=headers)
                    resp.raise_for_status()

                    data = resp.json()

                    if isinstance(data, list):
                        return {
                            "results": data,
                            "next": None,
                            "previous": None,
                        }

                    if isinstance(data, dict):
                        if "results" in data:
                            return data

                        if "id" in data:
                            return {
                                "results": [data],
                                "next": None,
                                "previous": None,
                            }

                    logger.warning(
                        "Unexpected provider response type: %s",
                        type(data),
                    )

                    return {
                        "results": [],
                        "next": None,
                        "previous": None,
                    }
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code

                if status_code in (500, 502, 503, 504):
                    logger.warning(
                        "Provider temporary error %s on attempt %s. Url: %s",
                        status_code,
                        attempt + 1,
                        url,
                    )

                    if attempt < 2:
                        await asyncio.sleep(2)
                        continue

                    return {
                        "results": [],
                        "next": None,
                    }

                raise

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                logger.warning(
                    "Provider connection error on attempt %s: %s",
                    attempt + 1,
                    exc,
                )

                if attempt < 2:
                    await asyncio.sleep(2)
                    continue

                return {
                    "results": [],
                    "next": None,
                }

        return {
            "results": [],
            "next": None,
        }

    async def fetch_all_events(
        self,
        changed_at: date,
    ) -> AsyncGenerator[Dict, None]:
        cursor = None

        while True:
            data = await self.fetch_events(changed_at, cursor)

            results = data.get("results") or []

            if not results:
                break

            for item in results:
                yield item

            next_url = data.get("next")

            if not next_url:
                break

            parsed = urlparse(next_url)
            cursor = parse_qs(parsed.query).get("cursor", [None])[0]

            if not cursor:
                break