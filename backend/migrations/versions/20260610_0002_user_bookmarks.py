"""add user bookmarks

Revision ID: 20260610_0002
Revises: 20260610_0001
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa


revision = "20260610_0002"
down_revision = "20260610_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_bookmarks",
        sa.Column("user_id", sa.String(length=120), nullable=False),
        sa.Column("itinerary_id", sa.String(length=180), nullable=False),
        sa.ForeignKeyConstraint(["itinerary_id"], ["itineraries.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("user_id", "itinerary_id"),
    )


def downgrade() -> None:
    op.drop_table("user_bookmarks")
