from typing import Literal

from pydantic import BaseModel, Field


class AnalysisRunCreate(BaseModel):
    company: str = Field(
        ...,
        min_length=2,
        description="Nom de domaine ou URL Trustpilot de l'entreprise à analyser.",
        examples=["www.darty.com", "https://fr.trustpilot.com/review/www.darty.com"],
    )
    source: Literal["trustpilot"] = Field(
        default="trustpilot",
        description="Source d'avis actuellement supportée.",
    )
    stars: list[int] = Field(
        default_factory=lambda: [1, 2, 3, 4, 5],
        description="Notes Trustpilot à collecter.",
        examples=[[1, 2, 3, 4, 5]],
    )
    pages_per_star: int = Field(
        default=1,
        ge=1,
        le=20,
        description="Nombre de pages Trustpilot à collecter pour chaque note.",
    )
    skip_scrape: bool = Field(
        default=False,
        description="Réutilise le JSON déjà présent pour le run quand c'est possible.",
    )
    execute_immediately: bool = Field(
        default=True,
        description="Envoie immédiatement le run dans la file Celery.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "company": "https://fr.trustpilot.com/review/www.darty.com",
                    "source": "trustpilot",
                    "stars": [1, 2, 3, 4, 5],
                    "pages_per_star": 1,
                    "execute_immediately": True,
                }
            ]
        }
    }


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
    celery_task_id: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    error_message: str | None = None


class AnalysisRunEventResponse(BaseModel):
    event_id: int
    run_id: int
    level: str
    step: str | None = None
    message: str
    created_at: str | None = None


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


class ErrorResponse(BaseModel):
    detail: str
