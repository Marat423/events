import pytest

from src.services.events_paginator import EventsPaginator


class FakeProviderClient:
    def __init__(self):
        self.calls = []

    async def fetch_events(self, changed_at, cursor=None):
        self.calls.append(cursor)

        if cursor is None:
            return {
                "results": [{"id": "1"}, {"id": "2"}],
                "next": "http://provider/api/events/?cursor=abc",
                "previous": None,
            }

        if cursor == "abc":
            return {
                "results": [{"id": "3"}],
                "next": None,
                "previous": None,
            }

        return {
            "results": [],
            "next": None,
            "previous": None,
        }


@pytest.mark.asyncio
async def test_events_paginator_iterates_all_pages():
    provider = FakeProviderClient()
    paginator = EventsPaginator(provider, changed_at="2000-01-01")

    result = []

    async for item in paginator:
        result.append(item)

    assert result == [
        {"id": "1"},
        {"id": "2"},
        {"id": "3"},
    ]
    assert provider.calls == [None, "abc"]
