import uuid

import psycopg2
import pytest
from psycopg2 import sql

from app.api.database import (
    PRODUCT_FOREIGN_KEY_REQUIREMENTS,
    PRODUCT_SCHEMA_REQUIREMENTS,
    SchemaMigrationError,
    ensure_product_schema,
    get_connection,
    get_db_config,
    get_schema_revision,
    run_schema_downgrade,
    run_schema_migrations,
)


HEAD_REVISION = "20260921_0008"


def _foreign_key_signatures(table_name):
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    ARRAY_AGG(source_attribute.attname ORDER BY source_column.ordinality),
                    target_table.relname,
                    ARRAY_AGG(target_attribute.attname ORDER BY source_column.ordinality)
                FROM pg_constraint constraint_row
                JOIN pg_class source_table
                  ON source_table.oid = constraint_row.conrelid
                JOIN pg_class target_table
                  ON target_table.oid = constraint_row.confrelid
                JOIN LATERAL UNNEST(constraint_row.conkey)
                  WITH ORDINALITY AS source_column(attribute_number, ordinality)
                  ON TRUE
                JOIN LATERAL UNNEST(constraint_row.confkey)
                  WITH ORDINALITY AS target_column(attribute_number, ordinality)
                  ON target_column.ordinality = source_column.ordinality
                JOIN pg_attribute source_attribute
                  ON source_attribute.attrelid = source_table.oid
                 AND source_attribute.attnum = source_column.attribute_number
                JOIN pg_attribute target_attribute
                  ON target_attribute.attrelid = target_table.oid
                 AND target_attribute.attnum = target_column.attribute_number
                WHERE constraint_row.contype = 'f'
                  AND source_table.relname = %s
                GROUP BY constraint_row.oid, target_table.relname;
                """,
                (table_name,),
            )
            return {
                (tuple(columns), referred_table, tuple(referred_columns))
                for columns, referred_table, referred_columns in cursor.fetchall()
            }


def _assert_critical_foreign_keys():
    for table_name, expected in PRODUCT_FOREIGN_KEY_REQUIREMENTS.items():
        assert expected <= _foreign_key_signatures(table_name)


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
    assert get_schema_revision() == {"current": HEAD_REVISION, "head": HEAD_REVISION}
    _assert_critical_foreign_keys()

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

    assert get_schema_revision()["current"] == HEAD_REVISION


def test_unversioned_database_missing_critical_foreign_key_is_rejected(
    temporary_database,
):
    ensure_product_schema()

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("DROP TABLE alembic_version;")
            cursor.execute(
                "ALTER TABLE companies "
                "DROP CONSTRAINT companies_organization_id_fkey;"
            )
        connection.commit()

    with pytest.raises(SchemaMigrationError, match="cle etrangere"):
        run_schema_migrations()

    assert "alembic_version" not in _table_names()


def test_corrective_foreign_keys_upgrade_and_downgrade_without_data_loss(
    temporary_database,
):
    ensure_product_schema()
    run_schema_downgrade("20260921_0007")

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT organization_id FROM organizations WHERE slug = 'demo';"
            )
            organization_id = cursor.fetchone()[0]
            cursor.execute(
                """
                INSERT INTO companies (
                    organization_id, company_name, trustpilot_slug, source_url
                ) VALUES (%s, 'FK marker', 'fk-marker.test', 'csv://fk-marker')
                RETURNING company_id;
                """,
                (organization_id,),
            )
            company_id = cursor.fetchone()[0]
            cursor.execute(
                """
                INSERT INTO analysis_runs (company_id, organization_id)
                VALUES (%s, %s)
                RETURNING run_id;
                """,
                (company_id, organization_id),
            )
            run_id = cursor.fetchone()[0]
            cursor.execute(
                """
                INSERT INTO model_training_runs (organization_id)
                VALUES (%s)
                RETURNING training_run_id;
                """,
                (organization_id,),
            )
            training_run_id = cursor.fetchone()[0]
            cursor.execute(
                "ALTER TABLE companies "
                "DROP CONSTRAINT companies_organization_id_fkey;"
            )
            cursor.execute(
                "ALTER TABLE analysis_runs "
                "DROP CONSTRAINT analysis_runs_organization_id_fkey;"
            )
            cursor.execute(
                "ALTER TABLE model_training_runs "
                "DROP CONSTRAINT model_training_runs_organization_id_fkey;"
            )
        connection.commit()

    assert run_schema_migrations() == "upgraded"
    _assert_critical_foreign_keys()

    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM companies WHERE company_id = %s;", (company_id,))
            assert cursor.fetchone()[0] == 1
            cursor.execute("SELECT COUNT(*) FROM analysis_runs WHERE run_id = %s;", (run_id,))
            assert cursor.fetchone()[0] == 1
            cursor.execute(
                "SELECT COUNT(*) FROM model_training_runs WHERE training_run_id = %s;",
                (training_run_id,),
            )
            assert cursor.fetchone()[0] == 1

    run_schema_downgrade("20260921_0007")
    assert get_schema_revision()["current"] == "20260921_0007"
    for table_name, expected in PRODUCT_FOREIGN_KEY_REQUIREMENTS.items():
        if table_name == "analysis_runs":
            expected = {
                signature for signature in expected if signature[0] != ("company_id",)
            }
        assert not (expected & _foreign_key_signatures(table_name))


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
