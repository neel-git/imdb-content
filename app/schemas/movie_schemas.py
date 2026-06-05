from typing import Literal
from pydantic import BaseModel, Field, field_validator

class ListMoviesQuery(BaseModel):
    """Validated + coerced query parameters for GET /api/v1/movies."""

    page: int = Field(default=1, ge=1, description="Page number (≥ 1)")
    page_size: int = Field(default=20, ge=1, le=100, description="Results per page (1–100)")
    year: int | None = Field(default=None, ge=1888, le=2100, description="Filter by release year")
    language: str | None = Field(default=None, max_length=100, description="Filter by language")
    sort_by: Literal["release_date", "ratings"] = Field(
        default="release_date",
        description="Field to sort by: release_date or ratings",
    )
    order: Literal["asc", "desc"] = Field(
        default="desc",
        description="Sort direction: asc or desc",
    )

    @field_validator("language", mode="before")
    @classmethod
    def normalise_language(cls, v: str | None) -> str | None:
        """Strip surrounding whitespace; treat blank string as absent."""
        if v is None:
            return None
        v = v.strip()
        return v if v else None

    model_config = {"extra": "ignore"}