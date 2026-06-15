"""initial database foundation

Revision ID: 20260610_0001
Revises:
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa


revision = "20260610_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "destinations",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("country", sa.String(length=255), nullable=False),
        sa.Column("region", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("supported", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "books",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("author", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("publication_year", sa.Integer(), nullable=True),
        sa.Column("public_domain", sa.Boolean(), nullable=False),
        sa.Column("themes", sa.JSON(), nullable=False),
        sa.Column("cover_url", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.String(length=80), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_table(
        "book_destinations",
        sa.Column("book_id", sa.String(length=120), nullable=False),
        sa.Column("destination_id", sa.String(length=120), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"]),
        sa.PrimaryKeyConstraint("book_id", "destination_id"),
    )
    op.create_table(
        "pois",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("destination_id", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=True),
        sa.Column("estimated_duration_minutes", sa.Integer(), nullable=False),
        sa.Column("ticketing_note", sa.Text(), nullable=True),
        sa.Column("literary_relevance", sa.Text(), nullable=False),
        sa.Column("verification_status", sa.String(length=40), nullable=False),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "itineraries",
        sa.Column("id", sa.String(length=180), nullable=False),
        sa.Column("destination_id", sa.String(length=120), nullable=False),
        sa.Column("book_id", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        sa.Column("transportation_mode", sa.String(length=40), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.Column("generated_from", sa.String(length=40), nullable=False),
        sa.Column("source_type", sa.String(length=60), nullable=True),
        sa.Column("source_itinerary_id", sa.String(length=180), nullable=True),
        sa.Column("adaptation_notes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(length=80), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.ForeignKeyConstraint(["destination_id"], ["destinations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "poi_books",
        sa.Column("poi_id", sa.String(length=120), nullable=False),
        sa.Column("book_id", sa.String(length=120), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"]),
        sa.ForeignKeyConstraint(["poi_id"], ["pois.id"]),
        sa.PrimaryKeyConstraint("poi_id", "book_id"),
    )
    op.create_table(
        "user_preferences",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("user_id", sa.String(length=120), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(length=80), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "user_reviews",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("user_id", sa.String(length=120), nullable=False),
        sa.Column("itinerary_id", sa.String(length=180), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(length=80), nullable=False),
        sa.ForeignKeyConstraint(["itinerary_id"], ["itineraries.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "itinerary_days",
        sa.Column("id", sa.String(length=180), nullable=False),
        sa.Column("itinerary_id", sa.String(length=180), nullable=False),
        sa.Column("day_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("estimated_distance_km", sa.Float(), nullable=True),
        sa.Column("estimated_duration_hours", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["itinerary_id"], ["itineraries.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "itinerary_stops",
        sa.Column("id", sa.String(length=220), nullable=False),
        sa.Column("day_id", sa.String(length=180), nullable=False),
        sa.Column("poi_id", sa.String(length=120), nullable=False),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("narrative_note", sa.Text(), nullable=False),
        sa.Column("logistics_note", sa.Text(), nullable=True),
        sa.Column("estimated_start_time", sa.String(length=40), nullable=True),
        sa.Column("estimated_end_time", sa.String(length=40), nullable=True),
        sa.ForeignKeyConstraint(["day_id"], ["itinerary_days.id"]),
        sa.ForeignKeyConstraint(["poi_id"], ["pois.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("itinerary_stops")
    op.drop_table("itinerary_days")
    op.drop_table("user_reviews")
    op.drop_table("user_preferences")
    op.drop_table("poi_books")
    op.drop_table("itineraries")
    op.drop_table("pois")
    op.drop_table("book_destinations")
    op.drop_table("users")
    op.drop_table("books")
    op.drop_table("destinations")
