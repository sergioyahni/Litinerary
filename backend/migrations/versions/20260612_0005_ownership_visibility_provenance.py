"""add ownership visibility provenance and licensing metadata

Revision ID: 20260612_0005
Revises: 20260611_0004
Create Date: 2026-06-12
"""
from alembic import op
import sqlalchemy as sa


revision = "20260612_0005"
down_revision = "20260611_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("auth_provider", sa.String(length=80), nullable=True))
    op.add_column("users", sa.Column("auth_subject", sa.String(length=255), nullable=True))
    op.add_column(
        "users",
        sa.Column("role", sa.String(length=40), nullable=False, server_default="user"),
    )
    op.add_column(
        "users",
        sa.Column(
            "subscription_status",
            sa.String(length=40),
            nullable=False,
            server_default="none",
        ),
    )
    op.add_column("users", sa.Column("updated_at", sa.String(length=80), nullable=True))
    op.add_column("itineraries", sa.Column("owner_user_id", sa.String(length=120), nullable=True))
    op.add_column(
        "itineraries",
        sa.Column("visibility", sa.String(length=40), nullable=False, server_default="public"),
    )
    op.add_column(
        "itineraries",
        sa.Column(
            "created_by_mode",
            sa.String(length=40),
            nullable=False,
            server_default="anonymous",
        ),
    )
    op.add_column(
        "itineraries",
        sa.Column("created_by_user_id", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "itineraries",
        sa.Column("subscriber_only", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("itineraries", sa.Column("updated_at", sa.String(length=80), nullable=True))
    op.add_column("itineraries", sa.Column("provider_name", sa.String(length=80), nullable=True))
    op.add_column("itineraries", sa.Column("provider_type", sa.String(length=80), nullable=True))
    op.add_column(
        "itineraries",
        sa.Column("provider_version", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "itineraries",
        sa.Column("provider_request_id", sa.String(length=180), nullable=True),
    )
    op.add_column(
        "itineraries",
        sa.Column("generated_by_service", sa.String(length=120), nullable=True),
    )
    op.add_column("itineraries", sa.Column("confidence_score", sa.Float(), nullable=True))
    op.add_column(
        "itineraries",
        sa.Column("provenance_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column("pois", sa.Column("provider_version", sa.String(length=120), nullable=True))
    op.add_column("pois", sa.Column("provider_request_id", sa.String(length=180), nullable=True))
    op.add_column("pois", sa.Column("last_verified_at", sa.String(length=80), nullable=True))
    op.add_column(
        "pois",
        sa.Column(
            "manual_review_status",
            sa.String(length=40),
            nullable=False,
            server_default="not_reviewed",
        ),
    )
    op.add_column("pois", sa.Column("reviewed_by_user_id", sa.String(length=120), nullable=True))
    op.add_column(
        "pois",
        sa.Column("provenance_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column("book_sources", sa.Column("source_license", sa.String(length=120), nullable=True))
    op.add_column(
        "book_sources",
        sa.Column(
            "copyright_status",
            sa.String(length=80),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.add_column(
        "book_sources",
        sa.Column(
            "allowed_processing_mode",
            sa.String(length=80),
            nullable=False,
            server_default="metadata_only",
        ),
    )
    op.add_column(
        "book_sources",
        sa.Column("source_notes", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column(
        "book_processing_artifacts",
        sa.Column("provider_name", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "book_processing_artifacts",
        sa.Column("provider_type", sa.String(length=80), nullable=True),
    )
    op.add_column(
        "book_processing_artifacts",
        sa.Column("provider_version", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "book_processing_artifacts",
        sa.Column("provider_request_id", sa.String(length=180), nullable=True),
    )
    op.add_column(
        "book_processing_artifacts",
        sa.Column("confidence_score", sa.Float(), nullable=True),
    )
    op.add_column(
        "book_processing_artifacts",
        sa.Column("provenance_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.create_table(
        "embedding_records",
        sa.Column("id", sa.String(length=160), nullable=False),
        sa.Column("source_resource_type", sa.String(length=80), nullable=False),
        sa.Column("source_resource_id", sa.String(length=180), nullable=False),
        sa.Column("collection_name", sa.String(length=120), nullable=False),
        sa.Column("embedding_provider", sa.String(length=120), nullable=False),
        sa.Column("embedding_model", sa.String(length=160), nullable=True),
        sa.Column("vector_dimension", sa.Integer(), nullable=True),
        sa.Column("vector_external_id", sa.String(length=255), nullable=True),
        sa.Column("last_embedded_at", sa.String(length=80), nullable=True),
        sa.Column("metadata_version", sa.String(length=40), nullable=False, server_default="1"),
        sa.Column("provenance_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("embedding_records")

    op.drop_column("book_processing_artifacts", "provenance_metadata")
    op.drop_column("book_processing_artifacts", "confidence_score")
    op.drop_column("book_processing_artifacts", "provider_request_id")
    op.drop_column("book_processing_artifacts", "provider_version")
    op.drop_column("book_processing_artifacts", "provider_type")
    op.drop_column("book_processing_artifacts", "provider_name")

    op.drop_column("book_sources", "source_notes")
    op.drop_column("book_sources", "allowed_processing_mode")
    op.drop_column("book_sources", "copyright_status")
    op.drop_column("book_sources", "source_license")

    op.drop_column("pois", "provenance_metadata")
    op.drop_column("pois", "reviewed_by_user_id")
    op.drop_column("pois", "manual_review_status")
    op.drop_column("pois", "last_verified_at")
    op.drop_column("pois", "provider_request_id")
    op.drop_column("pois", "provider_version")

    op.drop_column("itineraries", "provenance_metadata")
    op.drop_column("itineraries", "confidence_score")
    op.drop_column("itineraries", "generated_by_service")
    op.drop_column("itineraries", "provider_request_id")
    op.drop_column("itineraries", "provider_version")
    op.drop_column("itineraries", "provider_type")
    op.drop_column("itineraries", "provider_name")
    op.drop_column("itineraries", "updated_at")
    op.drop_column("itineraries", "subscriber_only")
    op.drop_column("itineraries", "created_by_user_id")
    op.drop_column("itineraries", "created_by_mode")
    op.drop_column("itineraries", "visibility")
    op.drop_column("itineraries", "owner_user_id")

    op.drop_column("users", "updated_at")
    op.drop_column("users", "subscription_status")
    op.drop_column("users", "role")
    op.drop_column("users", "auth_subject")
    op.drop_column("users", "auth_provider")
