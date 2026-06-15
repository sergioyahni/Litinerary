"""add poi verification metadata

Revision ID: 20260611_0004
Revises: 20260611_0003
Create Date: 2026-06-11
"""
from alembic import op
import sqlalchemy as sa


revision = "20260611_0004"
down_revision = "20260611_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pois", sa.Column("verification_provider", sa.String(length=80), nullable=True))
    op.add_column("pois", sa.Column("verification_confidence", sa.Float(), nullable=True))
    op.add_column("pois", sa.Column("verified_name", sa.String(length=255), nullable=True))
    op.add_column("pois", sa.Column("verified_address", sa.String(length=500), nullable=True))
    op.add_column("pois", sa.Column("verified_latitude", sa.Float(), nullable=True))
    op.add_column("pois", sa.Column("verified_longitude", sa.Float(), nullable=True))
    op.add_column("pois", sa.Column("opening_hours_note", sa.Text(), nullable=True))
    op.add_column("pois", sa.Column("ticketing_url", sa.String(length=500), nullable=True))
    op.add_column(
        "pois",
        sa.Column("verification_notes", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )


def downgrade() -> None:
    op.drop_column("pois", "verification_notes")
    op.drop_column("pois", "ticketing_url")
    op.drop_column("pois", "opening_hours_note")
    op.drop_column("pois", "verified_longitude")
    op.drop_column("pois", "verified_latitude")
    op.drop_column("pois", "verified_address")
    op.drop_column("pois", "verified_name")
    op.drop_column("pois", "verification_confidence")
    op.drop_column("pois", "verification_provider")
