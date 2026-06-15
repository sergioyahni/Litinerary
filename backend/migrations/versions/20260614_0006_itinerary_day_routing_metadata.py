"""Add itinerary day routing metadata fields."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260614_0006"
down_revision: str | None = "20260612_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "itinerary_days",
        sa.Column("route_geometry", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column(
        "itinerary_days",
        sa.Column("routing_provider_metadata", sa.JSON(), nullable=True),
    )
    op.add_column(
        "itinerary_days",
        sa.Column("routing_warnings", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("itinerary_days", "routing_warnings")
    op.drop_column("itinerary_days", "routing_provider_metadata")
    op.drop_column("itinerary_days", "route_geometry")
