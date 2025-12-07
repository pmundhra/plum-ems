"""Pagination models and utilities"""

from math import ceil
from typing import Any, Generic, TypeVar
from urllib.parse import urlencode

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pagination query parameters"""

    limit: int = Field(
        default=50,
        ge=1,
        le=100,
        description="Items per page (1-100)",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of items to skip",
    )


class PaginationMeta(BaseModel):
    """Pagination metadata"""

    total: int = Field(..., description="Total items across all pages")
    limit: int = Field(..., description="Current page size")
    offset: int = Field(..., description="Current offset")
    has_more: bool = Field(..., description="Whether there are more pages")
    current_page: int = Field(..., description="Current page number (1-indexed)")
    total_pages: int = Field(..., description="Total number of pages")


class PaginatedResponse(BaseModel, Generic[T]):
    """Paginated response wrapper"""

    object: str = Field(..., description="Object type (e.g., 'endorsement.list')")
    data: list[T] = Field(..., description="List of items")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")

    @classmethod
    def create(
        cls,
        data: list[T],
        total: int,
        limit: int,
        offset: int,
        object_type: str,
    ) -> "PaginatedResponse[T]":
        """
        Create a paginated response.

        Args:
            data: List of items for current page
            total: Total number of items
            limit: Items per page
            offset: Current offset
            object_type: Object type string (e.g., 'endorsement.list')

        Returns:
            PaginatedResponse instance
        """
        current_page = (offset // limit) + 1 if limit > 0 else 1
        total_pages = ceil(total / limit) if limit > 0 else 0
        has_more = (offset + len(data)) < total

        pagination = PaginationMeta(
            total=total,
            limit=limit,
            offset=offset,
            has_more=has_more,
            current_page=current_page,
            total_pages=total_pages,
        )

        return cls(
            object=object_type,
            data=data,
            pagination=pagination,
        )


def build_link_header(
    base_url: str,
    total: int,
    limit: int,
    offset: int,
) -> str | None:
    """
    Build RFC 5988 Link header for pagination navigation.

    Args:
        base_url: Base URL for the endpoint (without query params)
        total: Total number of items
        limit: Items per page
        offset: Current offset

    Returns:
        Link header string or None if no links needed
    """
    if limit <= 0:
        return None

    links = []

    # First page
    first_offset = 0
    first_url = f"{base_url}?{urlencode({'limit': limit, 'offset': first_offset})}"
    links.append(f'<{first_url}>; rel="first"')

    # Previous page
    if offset > 0:
        prev_offset = max(0, offset - limit)
        prev_url = f"{base_url}?{urlencode({'limit': limit, 'offset': prev_offset})}"
        links.append(f'<{prev_url}>; rel="prev"')

    # Next page
    if (offset + limit) < total:
        next_offset = offset + limit
        next_url = f"{base_url}?{urlencode({'limit': limit, 'offset': next_offset})}"
        links.append(f'<{next_url}>; rel="next"')

    # Last page
    last_offset = ((total - 1) // limit) * limit
    if last_offset >= 0 and last_offset != offset:
        last_url = f"{base_url}?{urlencode({'limit': limit, 'offset': last_offset})}"
        links.append(f'<{last_url}>; rel="last"')

    return ", ".join(links) if links else None
