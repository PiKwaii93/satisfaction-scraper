from typing import Literal

from pydantic import BaseModel, Field


class AnalysisRunCreate(BaseModel):
    company: str = Field(
        ...,
        min_length=2,
        examples=["www.darty.com", "https://fr.trustpilot.com/review/www.darty.com"],
    )
    source: Literal["trustpilot"] = "trustpilot"
    stars: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5])
    pages_per_star: int = Field(default=1, ge=1, le=20)
    skip_scrape: bool = False
    execute_immediately: bool = True


class AnalysisRunResponse(BaseModel):
    run_id: int
    company_id: int
    company_name: str
    trustpilot_slug: str
    source: str
    status: str
    pages_per_star: int
    stars_requested: list[int]
    total_reviews: int
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error_message: str | None = None


class ReviewResponse(BaseModel):
    review_id: int
    rating: int | None
    author_name: str | None
    raw_date: str | None
    verbatim: str | None
    company_responded: bool
    sentiment_label: str
    sentiment_score: float
    topics: list[str] = Field(default_factory=list)


class ReviewListResponse(BaseModel):
    run_id: int
    total: int
    limit: int
    offset: int
    reviews: list[ReviewResponse]
