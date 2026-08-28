"""enforce itinerary owner relationship and access indexes

Revision ID: 20260815_0008
Revises: 20260614_0007
Create Date: 2026-08-15
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260815_0008"
down_revision: str | None = "20260614_0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE itineraries
        SET visibility = CASE WHEN is_public THEN 'public' ELSE 'private' END
        WHERE visibility IS NULL OR visibility = ''
        """
    )
    op.execute(
        """
        UPDATE itineraries
        SET is_public = 0
        WHERE visibility IN ('private', 'unlisted')
        """
    )
    op.execute(
        """
        UPDATE itineraries
        SET owner_user_id = NULL
        WHERE owner_user_id IS NOT NULL
          AND owner_user_id NOT IN (SELECT id FROM users)
        """
    )
    op.execute(
        """
        UPDATE itineraries
        SET created_by_user_id = NULL
        WHERE created_by_user_id IS NOT NULL
          AND created_by_user_id NOT IN (SELECT id FROM users)
        """
    )
    with op.batch_alter_table("itineraries") as batch_op:
        batch_op.create_foreign_key(
            "fk_itineraries_owner_user_id_users",
            "users",
            ["owner_user_id"],
            ["id"],
            ondelete="SET NULL",
        )

    op.create_index(
        "ix_itineraries_public_visibility",
        "itineraries",
        ["is_public", "visibility"],
    )
    op.create_index(
        "ix_itineraries_owner_visibility",
        "itineraries",
        ["owner_user_id", "visibility"],
    )
    op.create_index(
        "ix_itineraries_source_itinerary_id",
        "itineraries",
        ["source_itinerary_id"],
    )
    op.create_index(
        "ix_chat_itinerary_references_itinerary_id",
        "chat_itinerary_references",
        ["itinerary_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_chat_itinerary_references_itinerary_id", table_name="chat_itinerary_references")
    op.drop_index("ix_itineraries_source_itinerary_id", table_name="itineraries")
    op.drop_index("ix_itineraries_owner_visibility", table_name="itineraries")
    op.drop_index("ix_itineraries_public_visibility", table_name="itineraries")
    with op.batch_alter_table("itineraries") as batch_op:
        batch_op.drop_constraint("fk_itineraries_owner_user_id_users", type_="foreignkey")
