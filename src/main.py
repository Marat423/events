from fastapi import FastAPI

from src.route import events, tickets, sync_provider

app = FastAPI()


@app.get("/api/health")
async def health():
    return {"status": "ok"}


app.include_router(events.router, prefix="/api")
app.include_router(tickets.router, prefix="/api")
app.include_router(sync_provider.router, prefix="/api")