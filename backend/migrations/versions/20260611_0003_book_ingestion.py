"""add book ingestion scaffolding

Revision ID: 20260611_0003
Revises: 20260610_0002
Create Date: 2026-06-11
"""
from alembic import op
import sqlalchemy as sa


revision = "20260611_0003"
down_revision = "20260610_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "book_sources",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("book_id", sa.String(length=120), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("reference_url", sa.String(length=500), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(length=80), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "book_ingestion_jobs",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("book_id", sa.String(length=120), nullable=False),
        sa.Column("source_id", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("extraction_notes", sa.JSON(), nullable=False),
        sa.Column("warnings", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(length=80), nullable=False),
        sa.Column("updated_at", sa.String(length=80), nullable=False),
        sa.Column("completed_at", sa.String(length=80), nullable=True),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.ForeignKeyConstraint(["source_id"], ["book_sources.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "book_location_candidates",
        sa.Column("id", sa.String(length=160), nullable=False),
        sa.Column("job_id", sa.String(length=120), nullable=False),
        sa.Column("book_id", sa.String(length=120), nullable=False),
        sa.Column("destination_id", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("literary_relevance", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("promoted_poi_id", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.String(length=80), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"]),
        sa.ForeignKeyConstraint(["job_id"], ["book_ingestion_jobs.id"]),
        sa.ForeignKeyConstraint(["promoted_poi_id"], ["pois.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "book_processing_artifacts",
        sa.Column("id", sa.String(length=160), nullable=False),
        sa.Column("job_id", sa.String(length=120), nullable=False),
        sa.Column("artifact_type", sa.String(length=80), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(length=80), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["book_ingestion_jobs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("book_processing_artifacts")
    op.drop_table("book_location_candidates")
    op.drop_table("book_ingestion_jobs")
    op.drop_table("book_sources")
