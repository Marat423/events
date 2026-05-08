from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    count: int
    next: Optional[str] = None
    previous: Optional[str] = None
    results: List[T]


def paginate_response(
    results: List, total: int, page: int, limit: int, base_url: str
) -> PaginatedResponse:
    next_url = None
    prev_url = None
    if page * limit < total:
        next_url = f"{base_url}?page={page + 1}&limit={limit}"
    if page > 1:
        prev_url = f"{base_url}?page={page - 1}&limit={limit}"
    return PaginatedResponse(
        count=total, next=next_url, previous=prev_url, results=results
    )
