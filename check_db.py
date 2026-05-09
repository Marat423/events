import asyncio
from sqlalchemy import text

from src.db.database import AsyncSessionLocal


EVENT_ID = "be4fb58d-ec0e-4ea1-8a26-8241edde8c43"


async def main():
    async with AsyncSessionLocal() as db:
        print("\n--- COUNTS ---")
        for table in ["places", "events", "seats", "tickets"]:
            result = await db.execute(text(f"SELECT COUNT(*) FROM {table}"))
            print(f"{table}:", result.scalar())

        print("\n--- EVENT + PLACE ---")
        result = await db.execute(
            text("""
                SELECT
                    e.id,
                    e.name,
                    e.status,
                    e.place_id,
                    p.name AS place_name,
                    p.seats_pattern
                FROM events e
                LEFT JOIN places p ON p.id = e.place_id
                WHERE e.id = CAST(:event_id AS uuid)
            """),
            {"event_id": EVENT_ID},
        )
        row = result.mappings().first()
        print(dict(row) if row else "event not found")

        print("\n--- SEATS COUNT FOR EVENT ---")
        result = await db.execute(
            text("""
                SELECT COUNT(*)
                FROM seats
                WHERE event_id = CAST(:event_id AS uuid)
            """),
            {"event_id": EVENT_ID},
        )
        print("seats for event:", result.scalar())

        print("\n--- FIRST 20 SEATS FOR EVENT ---")
        result = await db.execute(
            text("""
                SELECT id, row, number, is_available
                FROM seats
                WHERE event_id = CAST(:event_id AS uuid)
                ORDER BY row, number
                LIMIT 20
            """),
            {"event_id": EVENT_ID},
        )
        rows = result.mappings().all()
        for row in rows:
            print(dict(row))

        print("\n--- EVENTS WITH SEATS ---")
        result = await db.execute(
            text("""
                SELECT event_id, COUNT(*) AS seats_count
                FROM seats
                GROUP BY event_id
                ORDER BY seats_count DESC
                LIMIT 10
            """)
        )
        rows = result.mappings().all()
        for row in rows:
            print(dict(row))


if __name__ == "__main__":
    asyncio.run(main())