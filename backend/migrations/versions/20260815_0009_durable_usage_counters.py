"""Add durable usage counter table.

Revision ID: 20260815_0009
Revises: 20260815_0008
Create Date: 2026-08-15
"""

from alembic import op
import sqlalchemy as sa


revision = "20260815_0009"
down_revision = "20260815_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "usage_limit_counters",
        sa.Column("id", sa.String(length=240), nullable=False),
        sa.Column("subject_type", sa.String(length=40), nullable=False),
        sa.Column("subject_key", sa.String(length=180), nullable=False),
        sa.Column("action", sa.String(length=80), nullable=False),
        sa.Column("window_start", sa.String(length=40), nullable=False),
        sa.Column("window_end", sa.String(length=40), nullable=False),
        sa.Column("units_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("limit_units", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(length=80), nullable=False),
        sa.Column("updated_at", sa.String(length=80), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "subject_type",
            "subject_key",
            "action",
            "window_start",
            name="uq_usage_limit_counter_window",
        ),
    )
    op.create_index(
        "ix_usage_limit_counters_subject_action",
        "usage_limit_counters",
        ["subject_type", "subject_key", "action"],
    )
    op.create_index(
        "ix_usage_limit_counters_window_end",
        "usage_limit_counters",
        ["window_end"],
    )


def downgrade() -> None:
    op.drop_index("ix_usage_limit_counters_window_end", table_name="usage_limit_counters")
    op.drop_index("ix_usage_limit_counters_subject_action", table_name="usage_limit_counters")
    op.drop_table("usage_limit_counters")
