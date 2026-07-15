import uuid

import psycopg2
import pytest
from psycopg2 import sql

from app.api.database import (
    PRODUCT_SCHEMA_REQUIREMENTS,
    SchemaMigrationError,
    ensure_product_schema,
    get_connection,
    get_db_config,
    get_schema_revision,
    run_schema_downgrade,
    run_schema_migrations,
)


@pytest.fixture
def temporary_database(monkeypatch):
    database_name = f"test_migrations_{uuid.uuid4().hex}"
    maintenance_config = get_db_config()
    maintenance_config["database"] = "postgres"

    maintenance_connection = psycopg2.connect(**maintenance_config)
    maintenance_connection.autocommit = True
    try:
        with maintenance_connection.cursor() as cursor:
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(database_name))
            )
    finally:
        maintenance_connection.close()

    monkeypatch.setenv("DB_NAME", database_name)
    monkeypatch.setenv("DEMO_ADMIN_PASSWORD", "migration-test-password")

    try:
        yield database_name
    finally:
        maintenance_connection = psycopg2.connect(**maintenance_config)
        maintenance_connection.autocommit = True
        try:
            with maintenance_connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = %s
                      AND pid <> pg_backend_pid();
                    """,
                    (database_name,),
                )
                cursor.execute(
                    sql.SQL("DROP DATABASE {}").format(sql.Identifier(database_name))
                )
        finally:
            maintenance_connection.close()


def _table_names():
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public';
                """
            )
            return {row[0] for row in cursor.fetchall()}


def test_fresh_database_upgrades_and_downgrades_without_touching_legacy_tables(
    temporary_database,
):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("CREATE TABLE legacy_marker (marker_id INTEGER PRIMARY KEY);")
        connection.commit()

    ensure_product_schema()

    assert set(PRODUCT_SCHEMA_REQUIREMENTS) <= _table_names()
    assert get_schema_revision() == {
        "current": "20260715_0004",
        "head": "20260715_0004",
    }

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM organizations WHERE slug = 'demo';")
            assert cursor.fetchone()[0] == 1
            cursor.execute(
                "SELECT COUNT(*) FROM users WHERE email = 'demo@satisfaction.local';"
            )
            assert cursor.fetchone()[0] == 1
            cursor.execute(
                """
                SELECT source_id, status
                FROM organization_review_sources
                WHERE organization_id = (
                    SELECT organization_id FROM organizations WHERE slug = 'demo'
                )
                ORDER BY source_id;
                """
            )
            sources = dict(cursor.fetchall())
            assert sources["trustpilot"] == "active"
            assert sources["csv"] == "active"

    run_schema_downgrade("base")

    remaining_tables = _table_names()
    assert "legacy_marker" in remaining_tables
    assert not (set(PRODUCT_SCHEMA_REQUIREMENTS) & remaining_tables)


def test_complete_unversioned_database_is_stamped_without_data_loss(
    temporary_database,
):
    ensure_product_schema()

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT organization_id FROM organizations WHERE slug = 'demo';"
            )
            organization_id = cursor.fetchone()[0]
            cursor.execute(
                """
                INSERT INTO companies (
                    organization_id,
                    company_name,
                    trustpilot_slug,
                    source_url
                )
                VALUES (%s, 'Migration marker', 'migration-marker.test', 'csv://marker');
                """,
                (organization_id,),
            )
            cursor.execute("DROP TABLE alembic_version;")
        connection.commit()

    assert run_schema_migrations() == "stamped"

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM companies WHERE trustpilot_slug = %s;",
                ("migration-marker.test",),
            )
            assert cursor.fetchone()[0] == 1

    assert get_schema_revision()["current"] == "20260715_0004"


def test_partial_unversioned_database_is_rejected(temporary_database):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE organizations (
                    organization_id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL
                );
                """
            )
        connection.commit()

    with pytest.raises(SchemaMigrationError, match="Schema produit partiel"):
        run_schema_migrations()

    assert "alembic_version" not in _table_names()
