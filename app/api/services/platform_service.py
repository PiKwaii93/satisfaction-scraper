from app.api.database import get_cursor


def serialize_platform_organization(row):
    return {
        "organization_id": int(row["organization_id"]),
        "name": row["name"],
        "slug": row["slug"],
        "plan": row["plan"],
        "active_users": int(row.get("active_users") or 0),
        "analysis_runs": int(row.get("analysis_runs") or 0),
        "total_reviews": int(row.get("total_reviews") or 0),
        "open_upgrade_requests": int(row.get("open_upgrade_requests") or 0),
        "created_at": row.get("created_at"),
        "updated_at": row.get("updated_at"),
    }


def list_platform_organizations(limit=100, offset=0):
    with get_cursor() as cursor:
        cursor.execute(
            """
            WITH user_counts AS (
                SELECT
                    organization_id,
                    COUNT(*) FILTER (
                        WHERE COALESCE(account_status, 'active') IN ('active', 'pending')
                    ) AS active_users
                FROM users
                GROUP BY organization_id
            ),
            run_counts AS (
                SELECT
                    organization_id,
                    COUNT(*) AS analysis_runs,
                    COALESCE(SUM(total_reviews), 0) AS total_reviews
                FROM analysis_runs
                GROUP BY organization_id
            ),
            upgrade_counts AS (
                SELECT
                    organization_id,
                    COUNT(*) FILTER (
                        WHERE status IN ('pending', 'approved')
                    ) AS open_upgrade_requests
                FROM upgrade_requests
                GROUP BY organization_id
            )
            SELECT
                o.organization_id,
                o.name,
                o.slug,
                o.plan,
                o.created_at,
                o.updated_at,
                COALESCE(uc.active_users, 0) AS active_users,
                COALESCE(rc.analysis_runs, 0) AS analysis_runs,
                COALESCE(rc.total_reviews, 0) AS total_reviews,
                COALESCE(upc.open_upgrade_requests, 0) AS open_upgrade_requests
            FROM organizations o
            LEFT JOIN user_counts uc ON uc.organization_id = o.organization_id
            LEFT JOIN run_counts rc ON rc.organization_id = o.organization_id
            LEFT JOIN upgrade_counts upc ON upc.organization_id = o.organization_id
            ORDER BY o.organization_id DESC
            LIMIT %s OFFSET %s;
            """,
            (limit, offset),
        )
        return [serialize_platform_organization(row) for row in cursor.fetchall()]
