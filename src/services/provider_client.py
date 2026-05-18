import asyncio
import logging
from datetime import date
from typing import Any
from urllib.parse import urljoin

import httpx

logger = logging.getLogger(__name__)


class ProviderClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/") + "/"
        self.api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key}

    def _url(self, path: str) -> str:
        return urljoin(self.base_url, path.lstrip("/"))

    async def fetch_events(
        self,
        changed_at: date,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        url = self._url("api/events/")
        params = {"changed_at": changed_at.isoformat()}

        if cursor:
            params["cursor"] = cursor

        last_error: Exception | None = None

        for attempt in range(3):
            try:
                async with httpx.AsyncClient(
                    follow_redirects=True,
                    timeout=30.0,
                ) as client:
                    response = await client.get(
                        url,
                        params=params,
                        headers=self._headers(),
                    )

                logger.info(
                    "Provider response: status=%s, url=%s, params=%s",
                    response.status_code,
                    url,
                    params,
                )

                response.raise_for_status()
                data = response.json()

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

                return {
                    "results": [],
                    "next": None,
                    "previous": None,
                }

            except httpx.HTTPStatusError as exc:
                last_error = exc
                status_code = exc.response.status_code

                if status_code in (500, 502, 503, 504) and attempt < 2:
                    await asyncio.sleep(2)
                    continue

                raise

            except (httpx.ConnectError, httpx.TimeoutException) as exc:
                last_error = exc

                if attempt < 2:
                    await asyncio.sleep(2)
                    continue

                raise

        if last_error:
            raise last_error

        return {
            "results": [],
            "next": None,
            "previous": None,
        }

    async def fetch_event_seats(self, event_id: str) -> list[str]:
        url = self._url(f"api/events/{event_id}/seats/")

        async with httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
        ) as client:
            response = await client.get(url, headers=self._headers())

        response.raise_for_status()
        data = response.json()

        return data.get("available_seats") or data.get("seats") or []

    async def register_ticket(
        self,
        event_id: str,
        first_name: str,
        last_name: str,
        email: str,
        seat: str,
    ) -> dict[str, Any]:
        url = self._url(f"api/events/{event_id}/register/")

        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=False,
        ) as client:
            response = await client.post(
                url,
                json={
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "seat": seat,
                },
                headers=self._headers(),
            )

        response.raise_for_status()
        return response.json()

    async def unregister_ticket(
        self,
        event_id: str,
        ticket_id: str,
    ) -> None:
        url = self._url(f"api/events/{event_id}/unregister/")

        async with httpx.AsyncClient(
            timeout=10.0,
            follow_redirects=False,
        ) as client:
            response = await client.request(
                "DELETE",
                url,
                json={"ticket_id": ticket_id},
                headers=self._headers(),
            )

        response.raise_for_status()
