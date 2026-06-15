"""Add subscriber chat foundation tables."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260614_0007"
down_revision: str | None = "20260614_0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_sessions",
        sa.Column("id", sa.String(length=160), primary_key=True),
        sa.Column("user_id", sa.String(length=120), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False, server_default="active"),
        sa.Column("created_at", sa.String(length=80), nullable=False),
        sa.Column("updated_at", sa.String(length=80), nullable=False),
        sa.Column("provider_name", sa.String(length=80), nullable=True),
        sa.Column("provider_type", sa.String(length=80), nullable=True),
        sa.Column("provider_version", sa.String(length=120), nullable=True),
        sa.Column("provider_request_id", sa.String(length=180), nullable=True),
        sa.Column("provenance_metadata", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(length=180), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(length=160),
            sa.ForeignKey("chat_sessions.id"),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.String(length=80), nullable=False),
        sa.Column("provider_name", sa.String(length=80), nullable=True),
        sa.Column("provider_type", sa.String(length=80), nullable=True),
        sa.Column("provider_version", sa.String(length=120), nullable=True),
        sa.Column("provider_request_id", sa.String(length=180), nullable=True),
        sa.Column("provenance_metadata", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_table(
        "chat_itinerary_references",
        sa.Column("id", sa.String(length=180), primary_key=True),
        sa.Column(
            "session_id",
            sa.String(length=160),
            sa.ForeignKey("chat_sessions.id"),
            nullable=False,
        ),
        sa.Column("itinerary_id", sa.String(length=180), nullable=False),
        sa.Column("source_itinerary_id", sa.String(length=180), nullable=True),
        sa.Column("refinement_prompt", sa.Text(), nullable=False),
        sa.Column("created_at", sa.String(length=80), nullable=False),
        sa.Column("provider_name", sa.String(length=80), nullable=True),
        sa.Column("provider_type", sa.String(length=80), nullable=True),
        sa.Column("provider_version", sa.String(length=120), nullable=True),
        sa.Column("provider_request_id", sa.String(length=180), nullable=True),
        sa.Column("confidence_score", sa.Float(), nullable=True),
        sa.Column("provenance_metadata", sa.JSON(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_table("chat_itinerary_references")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
