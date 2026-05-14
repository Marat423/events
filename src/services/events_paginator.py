from datetime import date
from typing import Any, AsyncIterator
from urllib.parse import parse_qs, urlparse

from src.services.provider_client import ProviderClient


class EventsPaginator:
    def __init__(
        self,
        provider: ProviderClient,
        changed_at: date,
    ) -> None:
        self.provider = provider
        self.changed_at = changed_at
        self.cursor: str | None = None
        self.buffer: list[dict[str, Any]] = []
        self.finished = False

    def __aiter__(self) -> AsyncIterator[dict[str, Any]]:
        return self

    async def __anext__(self) -> dict[str, Any]:
        if not self.buffer and not self.finished:
            await self._load_next_page()

        if self.buffer:
            return self.buffer.pop(0)

        raise StopAsyncIteration

    async def _load_next_page(self) -> None:
        data = await self.provider.fetch_events(
            changed_at=self.changed_at,
            cursor=self.cursor,
        )

        results = data.get("results") or []
        self.buffer.extend(results)

        next_url = data.get("next")

        if not next_url:
            self.finished = True
            return

        parsed = urlparse(next_url)
        self.cursor = parse_qs(parsed.query).get("cursor", [None])[0]

        if not self.cursor:
            self.finished = True