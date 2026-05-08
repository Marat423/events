from typing import List

import httpx

from src.schemas.schemas import EventSchema


async def fetch_events_from_source(base_url: str, api_key: str) -> List[EventSchema]:
    url = f"{base_url.rstrip('/')}/api/events"
    headers = {"Authorization": f"Bearer {api_key}"}
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, timeout=10.0)
        response.raise_for_status()
        data = response.json()
    events = [EventSchema(**item) for item in data]
    return events
