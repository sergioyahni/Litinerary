"""add public itinerary book and destination snapshots

Revision ID: 20260928_0010
Revises: 20260815_0009
Create Date: 2026-09-28
"""
from alembic import op
import sqlalchemy as sa


revision = "20260928_0010"
down_revision = "20260815_0009"
branch_labels = None
depends_on = None


SQLITE_NAMING_CONVENTION = {
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
}
SQLITE_BOOK_FOREIGN_KEY = "fk_itineraries_book_id_books"


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint("itineraries_book_id_fkey", "itineraries", type_="foreignkey")
    elif bind.dialect.name == "sqlite":
        with op.batch_alter_table(
            "itineraries",
            naming_convention=SQLITE_NAMING_CONVENTION,
        ) as batch_op:
            batch_op.drop_constraint(SQLITE_BOOK_FOREIGN_KEY, type_="foreignkey")

    op.add_column("itineraries", sa.Column("book_title", sa.String(length=255), nullable=True))
    op.add_column("itineraries", sa.Column("book_author", sa.String(length=255), nullable=True))
    op.add_column("itineraries", sa.Column("book_description", sa.Text(), nullable=True))
    op.add_column("itineraries", sa.Column("book_publication_year", sa.Integer(), nullable=True))
    op.add_column("itineraries", sa.Column("book_public_domain", sa.Boolean(), nullable=True))
    op.add_column(
        "itineraries",
        sa.Column("book_themes", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    )
    op.add_column("itineraries", sa.Column("book_cover_url", sa.String(length=500), nullable=True))
    op.add_column("itineraries", sa.Column("book_source_type", sa.String(length=80), nullable=True))
    op.add_column("itineraries", sa.Column("book_provider_id", sa.String(length=180), nullable=True))
    op.add_column(
        "itineraries",
        sa.Column(
            "book_provenance_metadata",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    op.add_column("itineraries", sa.Column("destination_name", sa.String(length=255), nullable=True))
    op.add_column(
        "itineraries", sa.Column("destination_country", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "itineraries", sa.Column("destination_region", sa.String(length=255), nullable=True)
    )
    op.add_column("itineraries", sa.Column("destination_description", sa.Text(), nullable=True))
    op.add_column("itineraries", sa.Column("destination_latitude", sa.Float(), nullable=True))
    op.add_column("itineraries", sa.Column("destination_longitude", sa.Float(), nullable=True))
    op.add_column(
        "itineraries", sa.Column("destination_image_url", sa.String(length=500), nullable=True)
    )
    op.add_column(
        "itineraries", sa.Column("destination_source_type", sa.String(length=80), nullable=True)
    )
    op.add_column(
        "itineraries", sa.Column("destination_provider_id", sa.String(length=180), nullable=True)
    )
    op.add_column(
        "itineraries",
        sa.Column(
            "destination_provenance_metadata",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )

    op.execute(
        """
        UPDATE itineraries
        SET
            book_title = books.title,
            book_author = books.author,
            book_description = books.description,
            book_publication_year = books.publication_year,
            book_public_domain = books.public_domain,
            book_themes = books.themes,
            book_cover_url = books.cover_url,
            book_source_type = 'repository'
        FROM books
        WHERE itineraries.book_id = books.id
        """
        if bind.dialect.name == "postgresql"
        else """
        UPDATE itineraries
        SET
            book_title = (SELECT title FROM books WHERE books.id = itineraries.book_id),
            book_author = (SELECT author FROM books WHERE books.id = itineraries.book_id),
            book_description = (SELECT description FROM books WHERE books.id = itineraries.book_id),
            book_publication_year = (SELECT publication_year FROM books WHERE books.id = itineraries.book_id),
            book_public_domain = (SELECT public_domain FROM books WHERE books.id = itineraries.book_id),
            book_themes = (SELECT themes FROM books WHERE books.id = itineraries.book_id),
            book_cover_url = (SELECT cover_url FROM books WHERE books.id = itineraries.book_id),
            book_source_type = 'repository'
        WHERE EXISTS (SELECT 1 FROM books WHERE books.id = itineraries.book_id)
        """
    )
    op.execute(
        """
        UPDATE itineraries
        SET
            destination_name = destinations.name,
            destination_country = destinations.country,
            destination_region = destinations.region,
            destination_description = destinations.description,
            destination_latitude = destinations.latitude,
            destination_longitude = destinations.longitude,
            destination_image_url = destinations.image_url,
            destination_source_type = 'repository'
        FROM destinations
        WHERE itineraries.destination_id = destinations.id
        """
        if bind.dialect.name == "postgresql"
        else """
        UPDATE itineraries
        SET
            destination_name = (SELECT name FROM destinations WHERE destinations.id = itineraries.destination_id),
            destination_country = (SELECT country FROM destinations WHERE destinations.id = itineraries.destination_id),
            destination_region = (SELECT region FROM destinations WHERE destinations.id = itineraries.destination_id),
            destination_description = (SELECT description FROM destinations WHERE destinations.id = itineraries.destination_id),
            destination_latitude = (SELECT latitude FROM destinations WHERE destinations.id = itineraries.destination_id),
            destination_longitude = (SELECT longitude FROM destinations WHERE destinations.id = itineraries.destination_id),
            destination_image_url = (SELECT image_url FROM destinations WHERE destinations.id = itineraries.destination_id),
            destination_source_type = 'repository'
        WHERE EXISTS (SELECT 1 FROM destinations WHERE destinations.id = itineraries.destination_id)
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    incompatible_count = bind.scalar(
        sa.text(
            """
            SELECT COUNT(*)
            FROM itineraries
            LEFT JOIN books ON books.id = itineraries.book_id
            WHERE books.id IS NULL
            """
        )
    )
    if incompatible_count:
        raise RuntimeError(
            "Cannot downgrade 20260928_0010 to 20260815_0009: "
            f"found {incompatible_count} itinerary row(s) whose book_id has no matching "
            "books row. The historical schema requires every itinerary to reference a "
            "persisted book and cannot represent external-book snapshots alone. Reconcile, "
            "archive, or explicitly remove the affected itineraries before retrying; no "
            "schema changes were applied."
        )

    for column in (
        "destination_provenance_metadata",
        "destination_provider_id",
        "destination_source_type",
        "destination_image_url",
        "destination_longitude",
        "destination_latitude",
        "destination_description",
        "destination_region",
        "destination_country",
        "destination_name",
        "book_provenance_metadata",
        "book_provider_id",
        "book_source_type",
        "book_cover_url",
        "book_themes",
        "book_public_domain",
        "book_publication_year",
        "book_description",
        "book_author",
        "book_title",
    ):
        op.drop_column("itineraries", column)

    if bind.dialect.name == "postgresql":
        op.create_foreign_key(
            "itineraries_book_id_fkey",
            "itineraries",
            "books",
            ["book_id"],
            ["id"],
        )
    elif bind.dialect.name == "sqlite":
        with op.batch_alter_table("itineraries") as batch_op:
            batch_op.create_foreign_key(
                SQLITE_BOOK_FOREIGN_KEY,
                "books",
                ["book_id"],
                ["id"],
            )
