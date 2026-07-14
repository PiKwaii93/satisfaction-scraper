from typing import Literal
from datetime import datetime

from pydantic import BaseModel, Field


class OrganizationResponse(BaseModel):
    organization_id: int
    name: str


class OrganizationSettingsResponse(BaseModel):
    organization_id: int
    name: str
    slug: str
    plan: Literal["free", "pro", "business"] = "business"
    default_source: Literal["trustpilot", "csv"] = "trustpilot"
    default_pages_per_star: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OrganizationSettingsUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    default_source: Literal["trustpilot", "csv"] | None = None
    default_pages_per_star: int | None = Field(default=None, ge=1, le=20)


class OrganizationPlanUpdate(BaseModel):
    plan: Literal["free", "pro", "business"]


class UpgradeRequestCreate(BaseModel):
    requested_plan: Literal["pro", "business"]
    source: str | None = Field(default=None, max_length=80)
    note: str | None = Field(default=None, max_length=500)
    metadata: dict = Field(default_factory=dict)


class UpgradeRequestStatusUpdate(BaseModel):
    status: Literal["pending", "approved", "rejected", "completed", "cancelled"]


class UpgradeRequestResponse(BaseModel):
    upgrade_request_id: int
    organization_id: int
    requested_plan: Literal["pro", "business"]
    current_plan: Literal["free", "pro", "business"]
    status: Literal["pending", "approved", "rejected", "completed", "cancelled"]
    source: str | None = None
    note: str | None = None
    metadata: dict = Field(default_factory=dict)
    requested_by_email: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    handled_at: datetime | None = None


class OrganizationUsageLimits(BaseModel):
    monthly_runs: int | None = None
    monthly_reviews: int | None = None
    csv_reviews_per_import: int | None = None
    members: int | None = None


class OrganizationUsageMetrics(BaseModel):
    monthly_runs: int = 0
    monthly_reviews: int = 0
    members: int = 0


class OrganizationUsageFeatures(BaseModel):
    benchmark: bool = False
    model_training: bool = False


class OrganizationUsageResponse(BaseModel):
    plan: Literal["free", "pro", "business"]
    plan_label: str
    period_start: datetime | None = None
    limits: OrganizationUsageLimits
    usage: OrganizationUsageMetrics
    features: OrganizationUsageFeatures


class OrganizationAuditEventResponse(BaseModel):
    audit_event_id: int
    event_type: str
    actor_email: str | None = None
    summary: str
    entity_type: str | None = None
    entity_id: int | None = None
    metadata: dict = Field(default_factory=dict)
    created_at: datetime | None = None


class ActionCenterCounts(BaseModel):
    open_alerts: int = 0
    critical_alerts: int = 0
    failed_runs: int = 0
    active_runs: int = 0
    pending_invitations: int = 0
    pending_upgrade_requests: int = 0
    training_ready_corrections: int = 0
    recent_completed_runs: int = 0


class ActionCenterItem(BaseModel):
    item_id: str
    item_type: str
    severity: Literal["critical", "warning", "info", "success"]
    title: str
    message: str
    action_label: str | None = None
    action_target: dict = Field(default_factory=dict)
    requires_admin: bool = False
    created_at: datetime | None = None


class ActionCenterResponse(BaseModel):
    counts: ActionCenterCounts
    items: list[ActionCenterItem] = Field(default_factory=list)


class AuthMeResponse(BaseModel):
    user_id: int
    email: str
    full_name: str | None = None
    role: str
    organization: OrganizationResponse


class AuthLoginRequest(BaseModel):
    email: str = Field(..., min_length=3, examples=["demo@satisfaction.local"])
    password: str = Field(..., min_length=1, examples=["demo-password"])


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthMeResponse


class OrganizationUserResponse(BaseModel):
    user_id: int
    email: str
    full_name: str | None = None
    role: Literal["admin", "member"]
    is_active: bool
    account_status: Literal["active", "pending", "inactive"] = "active"
    created_at: datetime | None = None
    invited_at: datetime | None = None
    activated_at: datetime | None = None
    invitation_expires_at: datetime | None = None
    invitation_accept_url: str | None = None


class OrganizationUserCreate(BaseModel):
    email: str = Field(..., min_length=3, examples=["analyste@societe.fr"])
    password: str = Field(..., min_length=8, examples=["mot-de-passe-demo"])
    full_name: str | None = Field(default=None, max_length=255)
    role: Literal["admin", "member"] = "member"


class OrganizationInvitationCreate(BaseModel):
    email: str = Field(..., min_length=3, examples=["analyste@societe.fr"])
    full_name: str | None = Field(default=None, max_length=255)
    role: Literal["admin", "member"] = "member"


class OrganizationInvitationAccept(BaseModel):
    token: str = Field(..., min_length=16)
    password: str = Field(..., min_length=8, examples=["nouveau-mot-de-passe"])
    full_name: str | None = Field(default=None, max_length=255)


class ReviewSourceResponse(BaseModel):
    source_id: str
    label: str
    status: Literal["active", "not_configured", "error", "planned"]
    category: str
    description: str
    primary_action: str | None = None
    setup_hint: str | None = None
    supports_analysis: bool
    is_configured: bool
    is_enabled: bool = False
    can_configure: bool = False
    last_error: str | None = None
    config: dict = Field(default_factory=dict)
    updated_at: datetime | None = None
    required_fields: list[str] = Field(default_factory=list)
    optional_fields: list[str] = Field(default_factory=list)
    column_aliases: dict[str, list[str]] = Field(default_factory=dict)


class ReviewSourceUpdate(BaseModel):
    enabled: bool | None = None


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


class CsvPreviewReview(BaseModel):
    row_number: int
    rating: int
    author: str
    date: str
    company_responded: bool
    verbatim: str


class CsvImportPreviewResponse(BaseModel):
    review_count: int
    skipped_rows: int
    detected_columns: dict[str, str]
    available_columns: list[str]
    preview_reviews: list[CsvPreviewReview]
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


class TrendMetricChange(BaseModel):
    metric: str
    label: str
    previous_value: float | None = None
    current_value: float | None = None
    delta: float | None = None
    direction: Literal["up", "down", "flat", "unknown"]
    unit: str | None = None


class TrendSentimentChange(BaseModel):
    label: str
    previous_count: int
    current_count: int
    previous_rate: float
    current_rate: float
    delta_count: int
    delta_rate: float
    direction: Literal["up", "down", "flat"]


class TrendTopicChange(BaseModel):
    topic: str
    previous_count: int
    current_count: int
    delta_count: int
    direction: Literal["up", "down", "flat", "new", "resolved"]


class AnalysisRunTrendResponse(BaseModel):
    current_run: AnalysisRunResponse
    previous_run: AnalysisRunResponse | None = None
    has_previous: bool
    executive_summary: str
    metrics: list[TrendMetricChange] = Field(default_factory=list)
    sentiment: list[TrendSentimentChange] = Field(default_factory=list)
    rising_topics: list[TrendTopicChange] = Field(default_factory=list)
    falling_topics: list[TrendTopicChange] = Field(default_factory=list)
    new_topics: list[TrendTopicChange] = Field(default_factory=list)
    resolved_topics: list[TrendTopicChange] = Field(default_factory=list)


class BusinessAlertResponse(BaseModel):
    alert_id: int
    organization_id: int
    run_id: int | None = None
    company_id: int | None = None
    company_name: str | None = None
    alert_type: str
    severity: Literal["info", "warning", "critical"]
    title: str
    message: str
    status: Literal["open", "acknowledged", "resolved"]
    metadata: dict = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None


class BusinessAlertStatusUpdate(BaseModel):
    status: Literal["open", "acknowledged", "resolved"]


class ErrorResponse(BaseModel):
    detail: str
