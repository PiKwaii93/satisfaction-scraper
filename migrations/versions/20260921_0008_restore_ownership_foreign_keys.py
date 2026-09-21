"""restore ownership foreign keys on historical schemas

Revision ID: 20260921_0008
Revises: 20260921_0007
Create Date: 2026-09-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260921_0008"
down_revision = "20260921_0007"
branch_labels = None
depends_on = None


FOREIGN_KEYS = (
    (
        "fk_companies_organization_id_organizations_corrective",
        "companies",
        ("organization_id",),
        "organizations",
        ("organization_id",),
    ),
    (
        "fk_analysis_runs_organization_id_organizations_corrective",
        "analysis_runs",
        ("organization_id",),
        "organizations",
        ("organization_id",),
    ),
    (
        "fk_model_training_runs_organization_id_organizations_corrective",
        "model_training_runs",
        ("organization_id",),
        "organizations",
        ("organization_id",),
    ),
)


def _foreign_key_exists(table_name, columns, referred_table, referred_columns):
    inspector = sa.inspect(op.get_bind())
    expected = (tuple(columns), referred_table, tuple(referred_columns))
    return any(
        (
            tuple(foreign_key.get("constrained_columns") or ()),
            foreign_key.get("referred_table"),
            tuple(foreign_key.get("referred_columns") or ()),
        )
        == expected
        for foreign_key in inspector.get_foreign_keys(table_name)
    )


def _constraint_exists(table_name, constraint_name):
    inspector = sa.inspect(op.get_bind())
    return any(
        foreign_key.get("name") == constraint_name
        for foreign_key in inspector.get_foreign_keys(table_name)
    )


def upgrade():
    for name, table, columns, referred_table, referred_columns in FOREIGN_KEYS:
        if _foreign_key_exists(table, columns, referred_table, referred_columns):
            continue
        op.create_foreign_key(
            name,
            table,
            referred_table,
            list(columns),
            list(referred_columns),
            ondelete="CASCADE",
        )


def downgrade():
    for name, table, _columns, _referred_table, _referred_columns in reversed(
        FOREIGN_KEYS
    ):
        if _constraint_exists(table, name):
            op.drop_constraint(name, table, type_="foreignkey")
