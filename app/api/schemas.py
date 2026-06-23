from typing import Literal
from datetime import datetime

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
    execution_duration_seconds: int | None = None
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
    corrected_label: str | None = None
    feedback_comment: str | None = None
    feedback_updated_at: datetime | None = None
    topics: list[str] = Field(default_factory=list)


class ReviewListResponse(BaseModel):
    run_id: int
    total: int
    limit: int
    offset: int
    reviews: list[ReviewResponse]


class ReviewFeedbackCreate(BaseModel):
    corrected_label: str = Field(
        ...,
        description="Label corrigÃ© par l'utilisateur: Positif, Neutre ou NÃ©gatif.",
        examples=["NÃ©gatif"],
    )
    comment: str | None = Field(
        default=None,
        max_length=500,
        description="Note optionnelle expliquant la correction.",
    )


class ReviewFeedbackResponse(BaseModel):
    feedback_id: int
    review_id: int
    run_id: int
    predicted_label: str
    corrected_label: str
    comment: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FeedbackCompanySummary(BaseModel):
    company_id: int
    company_name: str
    correction_count: int
    changed_label_count: int
    run_count: int
    latest_feedback_at: datetime | None = None


class FeedbackLabelDistribution(BaseModel):
    label: str
    count: int


class FeedbackTransition(BaseModel):
    predicted_label: str
    corrected_label: str
    count: int


class FeedbackRecentCorrection(BaseModel):
    feedback_id: int
    review_id: int
    run_id: int
    company_name: str
    rating: int | None = None
    predicted_label: str
    corrected_label: str
    feedback_comment: str | None = None
    feedback_updated_at: datetime | None = None
    verbatim: str | None = None


class FeedbackQualityResponse(BaseModel):
    total_corrections: int
    changed_label_count: int
    confirmed_label_count: int
    apparent_error_rate: float
    training_ready_count: int
    corrected_company_count: int
    corrected_run_count: int
    latest_feedback_at: datetime | None = None
    by_company: list[FeedbackCompanySummary] = Field(default_factory=list)
    corrected_label_distribution: list[FeedbackLabelDistribution] = Field(
        default_factory=list
    )
    transitions: list[FeedbackTransition] = Field(default_factory=list)
    recent_corrections: list[FeedbackRecentCorrection] = Field(default_factory=list)


class ModelTrainingRunCreate(BaseModel):
    feedback_sample_weight: float | None = Field(
        default=None,
        ge=1.0,
        le=50.0,
        description="Poids applique aux corrections humaines. Null utilise la configuration serveur.",
    )
    execute_immediately: bool = Field(
        default=True,
        description="Envoie immediatement le reentrainement dans la file Celery.",
    )


class ProductionModelInfo(BaseModel):
    name: str
    alias: str
    version: str
    run_id: str | None = None
    source: str | None = None
    model_uri: str


class ModelTrainingRunResponse(BaseModel):
    training_run_id: int
    status: str
    celery_task_id: str | None = None
    trigger_source: str
    feedback_sample_weight: float | None = None
    training_rows: int
    training_manual_rows: int
    training_feedback_rows: int
    training_effective_rows: float | None = None
    accuracy: float | None = None
    macro_f1: float | None = None
    weighted_f1: float | None = None
    model_version: str | None = None
    mlflow_run_id: str | None = None
    model_uri: str | None = None
    error_message: str | None = None
    created_at: str | None = None
    started_at: str | None = None
    finished_at: str | None = None
    execution_duration_seconds: int | None = None


class ModelTrainingOverviewResponse(BaseModel):
    production_model: ProductionModelInfo | None = None
    latest_run: ModelTrainingRunResponse | None = None
    active_run: ModelTrainingRunResponse | None = None
    runs: list[ModelTrainingRunResponse] = Field(default_factory=list)


class BenchmarkTopicCount(BaseModel):
    topic: str
    count: int


class BenchmarkCompanyTopic(BaseModel):
    run_id: int
    company_name: str
    count: int


class BenchmarkCommonTopic(BaseModel):
    topic: str
    total_count: int
    run_count: int
    companies: list[BenchmarkCompanyTopic] = Field(default_factory=list)


class BenchmarkCompany(BaseModel):
    run_id: int
    company_name: str
    review_count: int
    text_count: int
    average_rating: float | None = None
    average_confidence: float | None = None
    health_score: int
    risk_level: str
    negative_count: int
    neutral_count: int
    positive_count: int
    negative_rate: float
    top_topics: list[BenchmarkTopicCount] = Field(default_factory=list)
    unique_topics: list[BenchmarkTopicCount] = Field(default_factory=list)


class BenchmarkHighlights(BaseModel):
    best_health: BenchmarkCompany | None = None
    highest_negative_rate: BenchmarkCompany | None = None
    most_reviews: BenchmarkCompany | None = None
    shared_priority: BenchmarkCommonTopic | None = None


class AnalysisRunsComparisonResponse(BaseModel):
    run_ids: list[int]
    companies: list[BenchmarkCompany] = Field(default_factory=list)
    common_topics: list[BenchmarkCommonTopic] = Field(default_factory=list)
    highlights: BenchmarkHighlights


class ErrorResponse(BaseModel):
    detail: str
