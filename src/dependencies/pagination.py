from fastapi import Query
from pydantic import BaseModel


class PaginationParams(BaseModel):
    page: int = Query(1, ge=1, description="Page number")
    page_size: int = Query(20, ge=1, le=100, description="Items per page")


def get_pagination_params(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, le=100),
) -> PaginationParams:
    return PaginationParams(page=page, page_size=page_size)
