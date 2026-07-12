from dataclasses import dataclass
from datetime import datetime

from app.api.database import get_cursor


REVIEWS_PER_TRUSTPILOT_PAGE_ESTIMATE = 24


class UsageLimitError(ValueError):
    """Raised when an organization reaches its current plan limits."""


class FeatureNotAvailableError(ValueError):
    """Raised when a feature is not included in the current plan."""


@dataclass(frozen=True)
class PlanLimits:
    label: str
    monthly_runs: int | None
    monthly_reviews: int | None
    csv_reviews_per_import: int | None
    members: int | None
    benchmark: bool
    model_training: bool


PLAN_LIMITS = {
    "free": PlanLimits(
        label="Free",
        monthly_runs=3,
        monthly_reviews=300,
        csv_reviews_per_import=100,
        members=1,
        benchmark=False,
        model_training=False,
    ),
    "pro": PlanLimits(
        label="Pro",
        monthly_runs=50,
        monthly_reviews=10_000,
        csv_reviews_per_import=2_000,
        members=5,
        benchmark=True,
        model_training=False,
    ),
    "business": PlanLimits(
        label="Business",
        monthly_runs=None,
        monthly_reviews=100_000,
        csv_reviews_per_import=10_000,
        members=25,
        benchmark=True,
        model_training=True,
    ),
}

DEFAULT_PLAN = "business"


def normalize_plan(plan: str | None) -> str:
    normalized = (plan or DEFAULT_PLAN).strip().lower()
    return normalized if normalized in PLAN_LIMITS else DEFAULT_PLAN


def get_organization_plan(organization_id: int) -> str:
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT plan
            FROM organizations
            WHERE organization_id = %s;
            """,
            (organization_id,),
        )
        row = cursor.fetchone()
    return normalize_plan(row["plan"] if row else None)


def _get_period_start():
    now = datetime.utcnow()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def get_monthly_usage(organization_id: int):
    period_start = _get_period_start()
    with get_cursor() as cursor:
        cursor.execute(
            """
            SELECT
                COUNT(*) FILTER (
                    WHERE status NOT IN ('failed')
                ) AS run_count,
                COALESCE(
                    SUM(total_reviews) FILTER (
                        WHERE status NOT IN ('failed', 'empty')
                    ),
                    0
                ) AS review_count
            FROM analysis_runs
            WHERE organization_id = %s
              AND created_at >= %s;
            """,
            (organization_id, period_start),
        )
        usage = cursor.fetchone() or {}

        cursor.execute(
            """
            SELECT COUNT(*) AS member_count
            FROM users
            WHERE organization_id = %s
              AND account_status IN ('active', 'pending');
            """,
            (organization_id,),
        )
        members = cursor.fetchone() or {}

    return {
        "period_start": period_start,
        "monthly_runs": int(usage.get("run_count") or 0),
        "monthly_reviews": int(usage.get("review_count") or 0),
        "members": int(members.get("member_count") or 0),
    }


def get_organization_usage(organization_id: int):
    plan = get_organization_plan(organization_id)
    limits = PLAN_LIMITS[plan]
    usage = get_monthly_usage(organization_id)
    return {
        "plan": plan,
        "plan_label": limits.label,
        "period_start": usage["period_start"],
        "limits": {
            "monthly_runs": limits.monthly_runs,
            "monthly_reviews": limits.monthly_reviews,
            "csv_reviews_per_import": limits.csv_reviews_per_import,
            "members": limits.members,
        },
        "usage": {
            "monthly_runs": usage["monthly_runs"],
            "monthly_reviews": usage["monthly_reviews"],
            "members": usage["members"],
        },
        "features": {
            "benchmark": limits.benchmark,
            "model_training": limits.model_training,
        },
    }


def _assert_under_limit(label: str, used: int, limit: int | None, increment=1):
    if limit is not None and used + increment > limit:
        raise UsageLimitError(
            f"Limite du plan atteinte pour {label}: {used}/{limit}."
        )


def assert_can_create_analysis(organization_id: int, estimated_reviews: int | None = None):
    plan = get_organization_plan(organization_id)
    limits = PLAN_LIMITS[plan]
    usage = get_monthly_usage(organization_id)
    _assert_under_limit("les analyses mensuelles", usage["monthly_runs"], limits.monthly_runs)
    if estimated_reviews is not None:
        _assert_under_limit(
            "les avis mensuels",
            usage["monthly_reviews"],
            limits.monthly_reviews,
            increment=max(0, int(estimated_reviews)),
        )


def assert_can_import_csv(organization_id: int, review_count: int):
    plan = get_organization_plan(organization_id)
    limits = PLAN_LIMITS[plan]
    usage = get_monthly_usage(organization_id)
    _assert_under_limit("les analyses mensuelles", usage["monthly_runs"], limits.monthly_runs)
    _assert_under_limit(
        "les avis par import CSV",
        0,
        limits.csv_reviews_per_import,
        increment=max(0, int(review_count)),
    )
    _assert_under_limit(
        "les avis mensuels",
        usage["monthly_reviews"],
        limits.monthly_reviews,
        increment=max(0, int(review_count)),
    )


def assert_can_add_member(organization_id: int):
    plan = get_organization_plan(organization_id)
    limits = PLAN_LIMITS[plan]
    usage = get_monthly_usage(organization_id)
    _assert_under_limit("les membres", usage["members"], limits.members)


def assert_feature_enabled(organization_id: int, feature: str):
    plan = get_organization_plan(organization_id)
    limits = PLAN_LIMITS[plan]
    enabled = {
        "benchmark": limits.benchmark,
        "model_training": limits.model_training,
    }.get(feature, False)
    if not enabled:
        raise FeatureNotAvailableError(
            f"Fonctionnalite indisponible avec le plan {limits.label}."
        )
