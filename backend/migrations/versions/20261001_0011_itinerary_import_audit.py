"""Add administrator itinerary import audit tables.

Revision ID: 20261001_0011
Revises: 20260928_0010
Create Date: 2026-10-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "20261001_0011"
down_revision: str | None = "20260928_0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "itinerary_import_jobs",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("batch_identity", sa.String(length=180), nullable=False),
        sa.Column("contract_version", sa.String(length=80), nullable=False),
        sa.Column("initiated_by_user_id", sa.String(length=120), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("artifact_hash", sa.String(length=64), nullable=False),
        sa.Column("artifact_json", sa.JSON(), nullable=False),
        sa.Column("preview_json", sa.JSON(), nullable=False),
        sa.Column("persisted_itinerary_ids", sa.JSON(), nullable=False),
        sa.Column("published_itinerary_ids", sa.JSON(), nullable=False),
        sa.Column("error_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(length=80), nullable=False),
        sa.Column("updated_at", sa.String(length=80), nullable=False),
        sa.Column("completed_at", sa.String(length=80), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_itinerary_import_jobs_batch_identity",
        "itinerary_import_jobs",
        ["batch_identity"],
        unique=False,
    )
    op.create_table(
        "itinerary_import_records",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("job_id", sa.String(length=120), nullable=False),
        sa.Column("source_identity", sa.String(length=180), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("contract_version", sa.String(length=80), nullable=False),
        sa.Column("itinerary_id", sa.String(length=180), nullable=False),
        sa.Column("publication_intent", sa.String(length=40), nullable=False),
        sa.Column("source_attribution", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.String(length=80), nullable=False),
        sa.Column("published_at", sa.String(length=80), nullable=True),
        sa.ForeignKeyConstraint(
            ["job_id"],
            ["itinerary_import_jobs.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_identity",
            name="uq_itinerary_import_records_source_identity",
        ),
    )
    op.create_index(
        "ix_itinerary_import_records_job_id",
        "itinerary_import_records",
        ["job_id"],
        unique=False,
    )
    op.create_index(
        "ix_itinerary_import_records_itinerary_id",
        "itinerary_import_records",
        ["itinerary_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_itinerary_import_records_itinerary_id",
        table_name="itinerary_import_records",
    )
    op.drop_index(
        "ix_itinerary_import_records_job_id",
        table_name="itinerary_import_records",
    )
    op.drop_table("itinerary_import_records")
    op.drop_index(
        "ix_itinerary_import_jobs_batch_identity",
        table_name="itinerary_import_jobs",
    )
    op.drop_table("itinerary_import_jobs")
