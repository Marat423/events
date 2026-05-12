import logging
from datetime import date

import httpx
from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select

from src.config import settings
from src.db import models
from src.db.database import AsyncSessionLocal
from src.services.background_sync import sync_once

router = APIRouter(prefix="/sync", tags=["sync"])

logger = logging.getLogger(__name__)


async def get_events_count() -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(func.count()).select_from(models.Event))
        return result.scalar() or 0


@router.post("/trigger")
async def trigger_sync():
    events_before = await get_events_count()

    try:
        count = await sync_once()
    except Exception as exc:
        logger.exception("Manual sync failed")

        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {type(exc).__name__}: {exc}",
        ) from exc

    events_after = await get_events_count()

    api_key = settings.EVENTS_API_KEY

    return {
        "status": "synced",
        "count": count,
        "events_before": events_before,
        "events_after": events_after,
        "source": "provider",
        "client_host": settings.CLIENT_HOST,
        "api_key_present": bool(api_key),
        "api_key_length": len(api_key),
        "api_key_start": api_key[:4],
        "api_key_end": api_key[-4:],
    }

@router.get("/provider-debug")
async def provider_debug():
    url = f"{settings.CLIENT_HOST.rstrip('/')}/api/events/"
    params = {"changed_at": date(2000, 1, 1).isoformat()}
    headers = {"x-api-key": settings.EVENTS_API_KEY}

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        response = await client.get(url, params=params, headers=headers)

    try:
        data = response.json()
    except Exception:
        data = response.text[:500]

    results_count = None

    if isinstance(data, dict):
        results = data.get("results")
        if isinstance(results, list):
            results_count = len(results)

    return {
        "status_code": response.status_code,
        "url": url,
        "params": params,
        "api_key_present": bool(settings.EVENTS_API_KEY),
        "api_key_length": len(settings.EVENTS_API_KEY),
        "api_key_start": settings.EVENTS_API_KEY[:4],
        "api_key_end": settings.EVENTS_API_KEY[-4:],
        "results_count": results_count,
        "response_preview": data,
    }