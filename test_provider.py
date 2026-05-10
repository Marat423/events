import asyncio

import httpx

from src.config import settings


async def main():
    print("CLIENT_HOST =", repr(settings.CLIENT_HOST))

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(
            settings.CLIENT_HOST.rstrip("/") + "/api/events/",
            params={"changed_at": "2000-01-01"},
            headers={"x-api-key": settings.EVENTS_API_KEY},
        )

    print("status:", response.status_code)
    print(response.text[:500])


if __name__ == "__main__":
    asyncio.run(main())